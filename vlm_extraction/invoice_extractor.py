"""
vlm_extraction/invoice_extractor.py

Orchestration layer: ties preprocessing (file -> PIL images) together
with the Gemini VLM client (PIL image -> structured dict) to produce
final structured invoice data for a given file path.

No preprocessing logic and no Gemini API logic lives here — this file
only coordinates the two.
"""

from typing import Any, Dict, List

from preprocessing.invoice_preprocessor import (
    preprocess_invoice,
    InvoicePreprocessingError,
)
from vlm_extraction.vlm_client import (
    generate_invoice_extraction,
    VLMConfigError,
    VLMRequestError,
    VLMResponseError,
    VLMParsingError,
)


# ---------------------------------------------------------------------------
# Custom exception for orchestration-level failures
# ---------------------------------------------------------------------------

class InvoiceExtractionError(Exception):
    """Raised when the end-to-end invoice extraction pipeline fails."""
    pass


# ---------------------------------------------------------------------------
# Multi-page merge logic
# ---------------------------------------------------------------------------

_SINGLE_VALUE_FIELDS = [
    "invoice_number",
    "invoice_date",
    "due_date",
    "vendor_name",
    "vendor_address",
    "customer_name",
    "customer_address",
    "currency",
    "subtotal",
    "tax",
    "total_amount",
]


def _merge_page_results(page_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {field: None for field in _SINGLE_VALUE_FIELDS}
    merged["line_items"] = []

    for page_data in page_results:
        if not isinstance(page_data, dict):
            continue

        for field in _SINGLE_VALUE_FIELDS:
            if merged[field] is None:
                value = page_data.get(field)
                if value is not None:
                    merged[field] = value

        page_line_items = page_data.get("line_items")
        if page_line_items:
            merged["line_items"].extend(page_line_items)

    merged["pages_extracted"] = len(page_results)
    merged["per_page_data"] = page_results

    return merged


# ---------------------------------------------------------------------------
# Main orchestration function
# ---------------------------------------------------------------------------

def extract_invoice_data(file_path: str) -> Dict[str, Any]:
    # Stage 1: file -> PIL image(s)
    try:
        images = preprocess_invoice(file_path)
    except InvoicePreprocessingError as e:
        raise InvoiceExtractionError(
            f"Preprocessing failed for '{file_path}': {e}"
        ) from e

    if not images:
        raise InvoiceExtractionError(
            f"Preprocessing returned no images for '{file_path}'."
        )

    # Stage 2: PIL image(s) -> Gemini VLM extraction
    page_results: List[Dict[str, Any]] = []
    for page_number, image in enumerate(images, start=1):
        try:
            page_data = generate_invoice_extraction(image)
        except (VLMConfigError, VLMRequestError, VLMResponseError, VLMParsingError) as e:
            raise InvoiceExtractionError(
                f"VLM extraction failed on page {page_number} of '{file_path}': {e}"
            ) from e

        page_results.append(page_data)

    # Stage 3: combine results
    if len(page_results) == 1:
        return page_results[0]

    return _merge_page_results(page_results)


# ---------------------------------------------------------------------------
# Manual test block
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    test_file = "sample_invoice.jpg"

    try:
        result = extract_invoice_data(test_file)
        print(f"Extraction successful for '{test_file}':\n")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except InvoiceExtractionError as e:
        print(f"Extraction failed: {e}")