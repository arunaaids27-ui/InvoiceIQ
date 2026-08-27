"""vlm_extraction/prompts.py

Holds the invoice extraction prompt text and the JSON schema used to
constrain the VLM's structured output (Gemini response_schema format).

No API calls here — pure prompt/schema definitions, reused by
vlm_client.py later.
"""

# ---------------------------------------------------------------------------
# JSON Schema for structured output
# Written in the format Gemini's `response_schema` expects
# (a subset of OpenAPI/JSON Schema: type, properties, items, nullable).
# ---------------------------------------------------------------------------

LINE_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "description": {"type": "string", "nullable": True},
        "quantity": {"type": "number", "nullable": True},
        "unit_price": {"type": "number", "nullable": True},
        "tax": {"type": "number", "nullable": True},
        "total": {"type": "number", "nullable": True},
    },
    "required": ["description", "quantity", "unit_price", "tax", "total"],
}

INVOICE_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "invoice_number": {"type": "string", "nullable": True},
        "invoice_date": {"type": "string", "nullable": True},
        "due_date": {"type": "string", "nullable": True},
        "vendor_name": {"type": "string", "nullable": True},
        "vendor_address": {"type": "string", "nullable": True},
        "customer_name": {"type": "string", "nullable": True},
        "customer_address": {"type": "string", "nullable": True},
        "currency": {"type": "string", "nullable": True},
        "line_items": {
            "type": "array",
            "items": LINE_ITEM_SCHEMA,
            "nullable": True,
        },
        "subtotal": {"type": "number", "nullable": True},
        "tax": {"type": "number", "nullable": True},
        "total_amount": {"type": "number", "nullable": True},
    },
    "required": [
        "invoice_number",
        "invoice_date",
        "due_date",
        "vendor_name",
        "vendor_address",
        "customer_name",
        "customer_address",
        "currency",
        "line_items",
        "subtotal",
        "tax",
        "total_amount",
    ],
}


# ---------------------------------------------------------------------------
# Extraction prompt
# ---------------------------------------------------------------------------

INVOICE_EXTRACTION_PROMPT = """You are an expert invoice data extraction system.

You will be shown an image of an invoice (which may be scanned, photographed,
or a rendered PDF page). Carefully read the entire document and extract the
following fields exactly as they appear on the invoice.

Fields to extract:
- invoice_number
- invoice_date
- due_date
- vendor_name
- vendor_address
- customer_name
- customer_address
- currency
- line_items (list of items, each with: description, quantity, unit_price, tax, total)
- subtotal
- tax
- total_amount

STRICT RULES:
1. Only extract information that is actually visible in the image. Do NOT
   guess, infer, or hallucinate any value that is not clearly present.
2. If a field is missing, unreadable, or not applicable to this invoice,
   set its value to null. Do not use empty strings, "N/A", "unknown", or
   placeholder text — use null.
3. For line_items, extract every distinct item row you can find. If no
   line items are visible at all, return an empty list [].
4. Within each line item, if a specific sub-field (e.g. tax per item) is
   not shown, set that sub-field to null — do not drop the field.
5. Preserve numbers as plain numeric values (no currency symbols, no
   thousands separators). Extract the currency symbol/code separately
   into the "currency" field (e.g. "USD", "INR", "RM").
6. Preserve dates exactly as written on the invoice (do not reformat or
   convert them).
7. Do not copy example values, do not fabricate vendor/customer names,
   and do not invent totals that are not printed on the document.
8. Return ONLY valid JSON matching the required schema. No explanations,
   no markdown formatting, no extra text outside the JSON object.

Extract the invoice data now.
"""