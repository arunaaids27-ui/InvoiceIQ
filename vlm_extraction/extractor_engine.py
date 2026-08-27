import os
import json
import re
from typing import List, Dict, Any, Optional
from PIL import Image
import pymupdf as fitz
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIGURABLE FIELD DEFINITIONS
# ============================================================
DEFAULT_EXTRACTION_FIELDS = [
    "invoice_number",
    "invoice_date",
    "vendor_name",
    "tax_amount",
    "total_amount",
    "line_items"
]

CRITICAL_MANDATORY_FIELDS = {"invoice_number", "invoice_date", "vendor_name", "total_amount"}

class InvoiceExtractionEngine:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment or constructor.")
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-2.5-flash"

    def preprocess_file(self, file_path: str) -> List[Image.Image]:
        """Validates format and converts PDF or image files to a list of RGB PIL Images."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        images = []

        try:
            if ext == ".pdf":
                doc = fitz.open(file_path)
                if doc.page_count == 0:
                    raise ValueError("Empty PDF document.")
                for page_num in range(doc.page_count):
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap(dpi=200)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    images.append(img)
                doc.close()
            elif ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"]:
                img = Image.open(file_path).convert("RGB")
                images.append(img)
            else:
                raise ValueError(f"Unsupported file format: {ext}")
        except Exception as e:
            raise RuntimeError(f"Corrupted or unreadable document: {str(e)}")

        return images

    def _build_dynamic_prompt(self, active_fields: List[str]) -> str:
        """Constructs an extraction prompt dynamically based on user-selected fields."""
        schema_props = {}
        for field in active_fields:
            if field == "line_items":
                schema_props["line_items"] = [
                    {
                        "description": "Item or service description",
                        "quantity": 1.0,
                        "unit_price": 0.0,
                        "total": 0.0
                    }
                ]
            elif "amount" in field or field in ["subtotal", "tax"]:
                schema_props[field] = "Float value or null"
            else:
                schema_props[field] = "String value or null"

        json_skeleton = json.dumps(schema_props, indent=2)

        prompt = f"""
You are an expert financial document intelligence system.
Analyze the provided document image and extract ONLY the requested fields.

RULES:
1. If a field is not physically present on the document, return null. DO NOT guess, infer, or hallucinate missing data.
2. Return amounts as numeric values without currency symbols.
3. Return dates in standard string format (YYYY-MM-DD where possible).

Extract into the following exact JSON structure:
{json_skeleton}

Return ONLY raw JSON. No markdown code blocks, no backticks.
"""
        return prompt

    def extract_single_invoice(
        self, 
        file_path: str, 
        active_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Extracts configured fields, evaluates confidence, and performs arithmetic validation."""
        fields_to_extract = active_fields or DEFAULT_EXTRACTION_FIELDS
        filename = os.path.basename(file_path)
        
        try:
            images = self.preprocess_file(file_path)
        except Exception as err:
            return {
                "status": "FAILED",
                "error_message": str(err),
                "extraction": {},
                "confidence_assessment": {
                    "overall_score": 0.0,
                    "overall_tier": "LOW",
                    "requires_manual_review": True,
                    "reasons": [str(err)]
                }
            }

        # Multi-page or single-page inference
        prompt = self._build_dynamic_prompt(fields_to_extract)
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[images[0], prompt],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )
            raw_text = response.text.strip()
            extracted_json = json.loads(raw_text)
        except Exception as e:
            return {
                "status": "FAILED",
                "error_message": f"VLM parsing error: {str(e)}",
                "extraction": {},
                "confidence_assessment": {
                    "overall_score": 0.0,
                    "overall_tier": "LOW",
                    "requires_manual_review": True,
                    "reasons": [f"API/JSON Decoding failure: {str(e)}"]
                }
            }

        # Validate & score extraction
        confidence_meta = self._score_and_validate(extracted_json, fields_to_extract)

        return {
            "status": "SUCCESS",
            "extraction": extracted_json,
            "confidence_assessment": confidence_meta
        }

    def _score_and_validate(
        self, 
        extracted: Dict[str, Any], 
        requested_fields: List[str]
    ) -> Dict[str, Any]:
        """Calculates field-level reliability, handles absent fields, and validates arithmetic."""
        field_scores = {}
        earned_score = 0.0
        total_possible_score = 0.0
        reasons = []

        # 1. Field-Level Scoring
        for field in requested_fields:
            val = extracted.get(field)
            is_critical = field in CRITICAL_MANDATORY_FIELDS
            weight = 2.0 if is_critical else 1.0
            total_possible_score += (100.0 * weight)

            if val is None or str(val).strip().lower() in ["", "null", "none", "n/a"]:
                if is_critical:
                    field_scores[field] = {
                        "score": 0,
                        "status": "MISSING_CRITICAL",
                        "indicator": "🔴 Needs Review"
                    }
                    reasons.append(f"Missing mandatory critical field: '{field}'")
                else:
                    field_scores[field] = {
                        "score": 100,
                        "status": "NOT_APPLICABLE",
                        "indicator": "⚪ N/A (Not on Document)"
                    }
                    earned_score += (100.0 * weight)
            else:
                field_scores[field] = {
                    "score": 100,
                    "status": "VERIFIED",
                    "indicator": "🟢 Verified (100%)"
                }
                earned_score += (100.0 * weight)

        # 2. Deterministic Arithmetic Cross-Validation
        arithmetic_valid = True
        total_val = extracted.get("total_amount")
        tax_val = extracted.get("tax_amount") or extracted.get("tax") or 0.0
        line_items = extracted.get("line_items", [])

        try:
            if total_val is not None:
                f_total = float(total_val)
                f_tax = float(tax_val)
                
                if isinstance(line_items, list) and len(line_items) > 0:
                    items_sum = sum(float(item.get("total", 0.0)) for item in line_items if isinstance(item, dict))
                    calculated_total = items_sum + f_tax
                    
                    if items_sum > 0 and abs(calculated_total - f_total) > 0.05:
                        arithmetic_valid = False
                        earned_score = max(0.0, earned_score - 30.0)
                        reasons.append(
                            f"Arithmetic mismatch: Line items sum ({items_sum:.2f}) + Tax ({f_tax:.2f}) "
                            f"does not equal Total Amount ({f_total:.2f})"
                        )
        except (ValueError, TypeError) as err:
            arithmetic_valid = False
            reasons.append(f"Numeric parse error during arithmetic check: {str(err)}")

        overall_score = round((earned_score / max(total_possible_score, 1.0)) * 100, 1)
        
        if overall_score >= 85.0 and arithmetic_valid:
            tier = "HIGH"
            status_code = "AUTO_ACCEPTED"
        elif overall_score >= 50.0:
            tier = "MODERATE"
            status_code = "NEEDS_REVIEW"
        else:
            tier = "LOW"
            status_code = "CRITICAL_REJECTION"

        return {
            "overall_score": overall_score,
            "overall_tier": tier,
            "status_code": status_code,
            "arithmetic_valid": arithmetic_valid,
            "requires_manual_review": overall_score < 85.0 or not arithmetic_valid,
            "reasons": reasons,
            "field_scores": field_scores
        }

    def process_batch(
        self, 
        file_paths: List[str], 
        active_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Processes multiple invoice files and aggregates output grouped by filename."""
        batch_results = {}
        for path in file_paths:
            fname = os.path.basename(path)
            batch_results[fname] = self.extract_single_invoice(path, active_fields)
        return batch_results