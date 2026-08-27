import os
import json
from typing import List, Dict, Any, Optional
from PIL import Image
import pymupdf as fitz
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

DEFAULT_EXTRACTION_FIELDS = [
    "invoice_number",
    "invoice_date",
    "vendor_name",
    "tax_amount",
    "total_amount",
    "line_items"
]

class InvoiceExtractionEngine:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment or .env file.")
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-3.6-flash"

    def preprocess_file(self, file_path: str) -> List[Image.Image]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: '{file_path}'")

        ext = os.path.splitext(file_path)[1].lower()
        images = []

        if ext == ".pdf":
            doc = fitz.open(file_path)
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
            raise ValueError(f"Unsupported format: {ext}")

        return images

    def _build_dynamic_prompt(self, active_fields: List[str]) -> str:
        schema_props = {}
        for field in active_fields:
            if field == "line_items":
                schema_props["line_items"] = [
                    {
                        "description": "Item description",
                        "quantity": 1.0,
                        "unit_price": 0.0,
                        "total": 0.0
                    }
                ]
            elif "amount" in field or field in ["subtotal", "tax", "tax_amount"]:
                schema_props[field] = 0.0
            else:
                schema_props[field] = "String value or null"

        json_skeleton = json.dumps(schema_props, indent=2)

        return f"""
You are an expert financial document intelligence system.
Analyze the document image and extract ONLY the requested fields.
If a field is not physically present on the document, return null. Do NOT hallucinate.

Extract into this exact JSON structure:
{json_skeleton}

Return ONLY raw JSON. No markdown backticks.
"""

    def extract_single_invoice(self, file_path: str, active_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        fields_to_extract = active_fields or DEFAULT_EXTRACTION_FIELDS
        try:
            images = self.preprocess_file(file_path)
            prompt = self._build_dynamic_prompt(fields_to_extract)
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[images[0], prompt],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )
            extracted_json = json.loads(response.text.strip())
        except Exception as e:
            return {"status": "FAILED", "error": str(e), "extraction": {}}

        return {"status": "SUCCESS", "extraction": extracted_json}

    def process_batch(self, file_paths: List[str], active_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        results = {}
        total_files = len(file_paths)
        for idx, path in enumerate(file_paths, 1):
            fname = os.path.basename(path)
            print(f"[{idx}/{total_files}] 🔄 Processing: {fname}...")
            results[fname] = self.extract_single_invoice(path, active_fields)
        return results


if __name__ == "__main__":
    engine = InvoiceExtractionEngine()

    custom_field_mapping = [
        "invoice_number",
        "invoice_date",
        "vendor_name",
        "tax_amount",
        "total_amount",
        "line_items"
    ]

    dataset_folder = "dataset"

    if not os.path.exists(dataset_folder):
        print(f"⚠️ Warning: '{dataset_folder}' folder illai. Root folder-la irukkura sample_invoice.jpg run panren.")
        invoice_batch = ["sample_invoice.jpg"]
    else:
        supported_exts = (".pdf", ".png", ".jpg", ".jpeg", ".webp")
        invoice_batch = [
            os.path.join(dataset_folder, f)
            for f in os.listdir(dataset_folder)
            if f.lower().endswith(supported_exts)
        ]

    print(f"🚀 Found {len(invoice_batch)} files in dataset. Starting extraction...")
    
    output_ledger = engine.process_batch(
        file_paths=invoice_batch, 
        active_fields=custom_field_mapping
    )

    output_filename = "dataset_results.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(output_ledger, f, indent=2)

    print(f"\n🎉 Completed! Full dataset results saved to '{output_filename}'")