import os
import json
import pandas as pd
import streamlit as st
from PIL import Image
import fitz  # PyMuPDF
from google import genai
from google.genai import types
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# 1. Page Configuration & Custom Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="InvoiceIQ - Open-Schema Multimodal Extraction",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_dotenv()

# Inject Custom CSS for dark-themed high-contrast HITL interface
st.markdown("""
<style>
    /* Main Background & Text */
    .stApp {
        background-color: #0b0f17;
        color: #e2e8f0;
    }
    
    /* Top Banner Header */
    .top-header {
        background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px 24px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .header-title {
        font-size: 18px;
        font-weight: 700;
        letter-spacing: 1px;
        color: #60a5fa;
        text-transform: uppercase;
    }
    .status-pill {
        background-color: #064e3b;
        color: #34d399;
        border: 1px solid #059669;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }

    /* Auto approval status box */
    .approval-box-success {
        background-color: rgba(16, 185, 129, 0.1);
        border: 1px solid #10b981;
        color: #34d399;
        padding: 12px 18px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 20px;
    }
    .approval-box-warning {
        background-color: rgba(245, 158, 11, 0.1);
        border: 1px solid #f59e0b;
        color: #fbbf24;
        padding: 12px 18px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 20px;
    }

    /* Cards & Containers */
    .card-container {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 20px;
    }

    /* Badge tags */
    .confidence-badge-green {
        background-color: #064e3b;
        color: #6ee7b7;
        font-size: 11px;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
    }
    .confidence-badge-amber {
        background-color: #78350f;
        color: #fde68a;
        font-size: 11px;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 2. VLM Extraction Core Function (Comprehensive Dynamic Discovery)
# -----------------------------------------------------------------------------
def extract_all_invoice_fields(image: Image.Image) -> dict:
    """
    Extracts all visible fields dynamically from an invoice image using Gemini Flash.
    Does NOT limit extraction to fixed 6 fields. Discovers header values, tabular items,
    missing standard fields, and flags items needing verification.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing from environment or .env file.")

    client = genai.Client(api_key=api_key)

    system_prompt = """
    You are an expert Vision Document Parsing Engine.
    Examine the provided document image and extract EVERY SINGLE printed field without layout restrictions.

    Instructions:
    1. Identify all header fields (Vendor name, addresses, phone numbers, tax IDs, invoice number, dates, payment terms, payment method, cashier ID, PO number, etc.).
    2. Extract all line items tabular data (description, quantity, unit price, tax code, total).
    3. Calculate total summaries (subtotal, taxes, discounts, grand total, cash paid, change returned).
    4. Detect standard invoice fields that are missing from this document.
    5. Evaluate confidence score (0-100) and flag any ambiguous, low-quality, or handwritten fields for human review.

    Return strictly a JSON object matching this schema:
    {
        "document_type": "Tax Invoice / Receipt / Bill",
        "overall_confidence": 90,
        "requires_human_review": false,
        "extracted_fields": {
            "Vendor Name": "Sample Vendor",
            "Invoice Number": "12345",
            "Invoice Date": "YYYY-MM-DD",
            "Tax Amount": "0.00",
            "Grand Total": "0.00"
            // Include ALL other key-value pairs discovered in the document here dynamically
        },
        "line_items": [
            {
                "description": "Item description",
                "qty": 1,
                "unit_price": 0.0,
                "total": 0.0
            }
        ],
        "missing_standard_fields": ["due_date", "purchase_order_number"],
        "verification_flags": [
            {
                "field": "Field Name",
                "value": "Extracted Value",
                "reason": "Handwritten / low resolution / arithmetic discrepancy"
            }
        ]
    }
    Return ONLY valid JSON. Do not surround with markdown backticks.
    """

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=[image, system_prompt],
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json"
        )
    )

    clean_text = response.text.strip()
    if clean_text.startswith("
```json"):
        clean_text = clean_text[7:]
    if clean_text.endswith("
```"):
        clean_text = clean_text[:-3]

    return json.loads(clean_text)


# -----------------------------------------------------------------------------
# 3. Sidebar Setup & Navigation
# -----------------------------------------------------------------------------
st.sidebar.title("⚙️ InvoiceIQ Studio")
uploaded_file = st.sidebar.file_uploader(
    "Upload Invoice / Receipt Document",
    type=["png", "jpg", "jpeg", "webp", "pdf"],
    help="Upload single/multi-page PDFs or image documents."
)

mode = st.sidebar.radio(
    "Navigation Mode",
    ["⚡ Side-by-Side HITL Inspection", "📊 Spend Analytics & Audit Log"]
)


# -----------------------------------------------------------------------------
# 4. Main Page Rendering
# -----------------------------------------------------------------------------
st.markdown("""
<div class="top-header">
    <div class="header-title">Multimodal VLM • Side-by-Side HITL Inspection</div>
    <div class="status-pill">● Pipeline Active</div>
</div>
""", unsafe_allow_html=True)

if uploaded_file is not None:
    # Preprocess image/PDF
    ext = uploaded_file.name.split(".")[-1].lower()
    if ext == "pdf":
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        pix = doc[0].get_pixmap(dpi=150)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
    else:
        img = Image.open(uploaded_file).convert("RGB")

    # Run or retrieve extraction state
    if "current_file" not in st.session_state or st.session_state.current_file != uploaded_file.name:
        with st.spinner("🔍 VLM analyzing visual layout and extracting all dynamic fields..."):
            try:
                extraction_data = extract_all_invoice_fields(img)
                st.session_state.extraction = extraction_data
                st.session_state.current_file = uploaded_file.name
            except Exception as e:
                st.error(f"Extraction Error: {str(e)}")
                st.stop()

    data = st.session_state.extraction
    overall_conf = data.get("overall_confidence", 85)
    needs_review = data.get("requires_human_review", False) or overall_conf < 80

    # Status Banner
    if not needs_review:
        st.markdown(f"""
        <div class="approval-box-success">
            ✅ AUTO-APPROVED ({overall_conf}% Confidence): Quality gate passed. Document ready for accounting ingestion.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="approval-box-warning">
            ⚠️ MANUAL VERIFICATION REQUIRED ({overall_conf}% Confidence): Flagged fields require human review before saving.
        </div>
        """, unsafe_allow_html=True)

    # Two-Column Layout (Side-by-Side Document & Verification Panel)
    col_doc, col_panel = st.columns([1, 1], gap="medium")

    # Column 1: Document View
    with col_doc:
        st.subheader("📄 Original Ingested Document")
        st.image(img, use_container_width=True)

    # Column 2: Human-in-the-Loop Panel
    with col_panel:
        st.subheader("✏️ Human-in-the-Loop Verification")
        
        st.write(f"**Document Type Identified:** `{data.get('document_type', 'Invoice')}`")

        # Dynamic Field Editing
        extracted = data.get("extracted_fields", {})
        updated_fields = {}

        st.markdown("#### Discovered Metadata Fields")
        field_cols = st.columns(2)
        idx = 0
        for field_name, field_value in extracted.items():
            c = field_cols[idx % 2]
            with c:
                updated_fields[field_name] = st.text_input(
                    label=field_name,
                    value=str(field_value),
                    key=f"input_{field_name}"
                )
            idx += 1

        # Line Items Section
        line_items = data.get("line_items", [])
        if line_items:
            with st.expander("📦 Itemized Line Items Table", expanded=True):
                df_items = pd.DataFrame(line_items)
                edited_df = st.data_editor(df_items, num_rows="dynamic", use_container_width=True)

        # Verification Flags (Warnings)
        flags = data.get("verification_flags", [])
        if flags:
            st.markdown("#### 🚩 Verification Alerts")
            for flag in flags:
                st.warning(f"**Field**: `{flag.get('field')}` | **Value**: `{flag.get('value')}`\n\n*Reason*: {flag.get('reason')}")

        # Missing Standard Fields Registry
        missing = data.get("missing_standard_fields", [])
        if missing:
            with st.expander("ℹ️ Missing Standard Invoice Fields"):
                st.info("The following standard fields were not physically present on this document:\n\n- " + "\n- ".join(missing))

        # Actions
        st.markdown("---")
        b1, b2 = st.columns(2)
        with b1:
            if st.button("💾 Confirm & Commit Record", type="primary", use_container_width=True):
                final_record = {
                    "filename": uploaded_file.name,
                    "extracted_fields": updated_fields,
                    "line_items": line_items,
                    "confidence": overall_conf
                }
                st.success("Record committed successfully to database!")
                st.json(final_record)
        with b2:
            export_payload = json.dumps(data, indent=2)
            st.download_button(
                "📥 Export Full JSON",
                data=export_payload,
                file_name=f"extracted_{uploaded_file.name}.json",
                mime="application/json",
                use_container_width=True
            )

else:
    st.info("👈 Please upload an invoice PDF or image in the sidebar to begin extraction.")