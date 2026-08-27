"""vlm_extraction/vlm_client.py

Handles all communication with the Gemini API (via the google-genai SDK)
for invoice extraction. This file is responsible ONLY for:
- Loading the API key securely
- Sending a PIL invoice image + extraction prompt to Gemini
- Requesting structured JSON output constrained to INVOICE_EXTRACTION_SCHEMA
- Safely parsing the response into a Python dict

No orchestration, no preprocessing, no UI logic lives here.
"""

import os
import re
import json
import time
import random
from typing import Any, Dict

from dotenv import load_dotenv
from PIL import Image
from google import genai
from google.genai import types
from google.genai import errors as genai_errors

from vlm_extraction.prompts import INVOICE_EXTRACTION_PROMPT, INVOICE_EXTRACTION_SCHEMA


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class VLMConfigError(Exception):
    """Raised when the API key or client configuration is missing/invalid."""
    pass


class VLMRequestError(Exception):
    """Raised when the Gemini API call itself fails (network, auth, quota, etc.)."""
    pass


class VLMResponseError(Exception):
    """Raised when Gemini returns an empty or otherwise unusable response."""
    pass


class VLMParsingError(Exception):
    """Raised when the response text cannot be parsed as valid JSON."""
    pass


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_NAME = "gemini-3.6-flash"

# Retry config for transient errors (503 UNAVAILABLE, high-demand, etc.)
MAX_RETRIES = 4          # total attempts = 1 initial + 4 retries = 5
BASE_DELAY_SECONDS = 2.0  # 2s, 4s, 8s, 16s ... (+ small jitter)

# HTTP status codes considered "transient" - safe to retry
RETRYABLE_STATUS_CODES = {503, 429, 500}

load_dotenv()  # loads variables from a local .env file, if present


def _get_client() -> genai.Client:
    """
    Builds and returns a genai.Client using GEMINI_API_KEY from the
    environment (loaded from .env via python-dotenv).
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise VLMConfigError(
            "GEMINI_API_KEY not found. Make sure it is set in your .env file "
            "as: GEMINI_API_KEY=your_key_here"
        )

    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        raise VLMConfigError(f"Failed to initialize Gemini client: {e}")


def _is_retryable_error(exc: Exception) -> bool:
    """
    Decides whether an exception represents a transient retryable error.
    """
    status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if status_code in RETRYABLE_STATUS_CODES:
        return True

    message = str(exc).lower()
    retry_tokens = ("503", "unavailable", "overloaded", "429", "rate limit", "getaddrinfo", "timeout")
    if any(token in message for token in retry_tokens):
        return True

    return False


def _call_gemini_with_retry(client: genai.Client, contents, config: types.GenerateContentConfig):
    """
    Calls client.models.generate_content with exponential backoff retry
    for transient errors (503/429/500/network drops).
    """
    last_exception: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            return client.models.generate_content(
                model=MODEL_NAME,
                contents=contents,
                config=config,
            )
        except genai_errors.APIError as e:
            last_exception = e
            if not _is_retryable_error(e) or attempt == MAX_RETRIES:
                raise VLMRequestError(f"Gemini API request failed: {e}")

            delay = BASE_DELAY_SECONDS * (2 ** attempt) + random.uniform(0, 0.5)
            print(
                f"[vlm_client] Transient error (attempt {attempt + 1}/{MAX_RETRIES + 1}): "
                f"{e}. Retrying in {delay:.1f}s..."
            )
            time.sleep(delay)
        except Exception as e:
            last_exception = e
            if attempt == MAX_RETRIES:
                raise VLMRequestError(f"Gemini API request failed: {e}")

            delay = BASE_DELAY_SECONDS * (2 ** attempt) + random.uniform(0, 0.5)
            print(
                f"[vlm_client] Request error (attempt {attempt + 1}/{MAX_RETRIES + 1}): "
                f"{e}. Retrying in {delay:.1f}s..."
            )
            time.sleep(delay)

    raise VLMRequestError(f"Gemini API request failed after retries: {last_exception}")


def _clean_json_markdown(text: str) -> str:
    """Helper to remove markdown code fence wrapping if returned."""
    clean_text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_text)
    if match:
        return match.group(1).strip()
    return clean_text


# ---------------------------------------------------------------------------
# Core extraction function
# ---------------------------------------------------------------------------

def generate_invoice_extraction(image: Image.Image) -> Dict[str, Any]:
    """
    Sends an invoice image to Gemini and returns extracted invoice data
    as a structured Python dictionary, matching INVOICE_EXTRACTION_SCHEMA.
    """
    if image is None:
        raise VLMConfigError("No image provided to generate_invoice_extraction().")

    client = _get_client()

    generation_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=INVOICE_EXTRACTION_SCHEMA,
    )

    response = _call_gemini_with_retry(
        client=client,
        contents=[INVOICE_EXTRACTION_PROMPT, image],
        config=generation_config,
    )

    raw_text = getattr(response, "text", None)
    if not raw_text or not raw_text.strip():
        raise VLMResponseError(
            "Gemini returned an empty response. The image may be unreadable, "
            "or the request may have been blocked (e.g. by safety filters)."
        )

    try:
        sanitized_json = _clean_json_markdown(raw_text)
        extracted_data: Dict[str, Any] = json.loads(sanitized_json)
    except (json.JSONDecodeError, TypeError) as e:
        raise VLMParsingError(
            f"Failed to parse Gemini response as JSON: {e}\nRaw response: {raw_text}"
        )

    return extracted_data