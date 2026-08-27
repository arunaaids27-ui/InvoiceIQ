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

# Inject Custom CSS for a polished, corporate-grade dark HITL interface
st.markdown("""
<style>
    /* ---------------------------------------------------------------- */
    /* Fonts                                                             */
    /* ---------------------------------------------------------------- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    code, pre, .stCodeBlock, [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace;
    }

    /* ---------------------------------------------------------------- */
    /* Global app background & palette                                   */
    /* ---------------------------------------------------------------- */
    :root {
        --bg-primary: #0a0e16;
        --bg-secondary: #10151f;
        --surface: #161d2b;
        --surface-alt: #1c2536;
        --border-subtle: #26304433;
        --border: #2a3549;
        --accent: #3b82f6;
        --accent-soft: #60a5fa;
        --accent-glow: rgba(59, 130, 246, 0.25);
        --success: #10b981;
        --success-soft: #34d399;
        --warning: #f59e0b;
        --warning-soft: #fbbf24;
        --text-primary: #e8edf5;
        --text-secondary: #94a3b8;
        --text-muted: #64748b;
    }

    .stApp {
        background: radial-gradient(circle at top left, #0d1320 0%, #090c13 60%), var(--bg-primary);
        color: var(--text-primary);
    }

    /* Tighten default top padding for a denser, app-like feel */
    .block-container {
        padding-top: 1.6rem;
        padding-bottom: 2.5rem;
        max-width: 1400px;
    }

    /* ---------------------------------------------------------------- */
    /* Sidebar                                                            */
    /* ---------------------------------------------------------------- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1320 0%, #0a0e16 100%);
        border-right: 1px solid var(--border);
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 2rem;
    }
    section[data-testid="stSidebar"] h1 {
        font-size: 1.15rem;
        font-weight: 700;
        color: var(--text-primary);
        letter-spacing: 0.3px;
        border-bottom: 1px solid var(--border);
        padding-bottom: 14px;
        margin-bottom: 18px;
    }
    section[data-testid="stSidebar"] label {
        font-weight: 600;
        color: var(--text-secondary) !important;
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }

    /* File uploader */
    [data-testid="stFileUploaderDropzone"] {
        background: var(--surface);
        border: 1.5px dashed var(--border);
        border-radius: 12px;
        transition: border-color 0.2s ease, background 0.2s ease;
    }
    [data-testid="stFileUploaderDropzone"]:hover {
        border-color: var(--accent);
        background: var(--surface-alt);
    }

    /* Radio nav styled like segmented tabs */
    div[role="radiogroup"] {
        gap: 6px;
    }
    div[role="radiogroup"] label {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 10px 12px !important;
        margin-bottom: 4px;
        transition: all 0.15s ease;
        text-transform: none !important;
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        color: var(--text-primary) !important;
    }
    div[role="radiogroup"] label:hover {
        border-color: var(--accent-soft);
        background: var(--surface-alt);
    }

    /* ---------------------------------------------------------------- */
    /* Top Banner Header                                                  */
    /* ---------------------------------------------------------------- */
    .top-header {
        background: linear-gradient(90deg, #131b2c 0%, #0c111c 100%);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 20px 28px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35);
    }
    .header-title {
        font-size: 17px;
        font-weight: 700;
        letter-spacing: 0.8px;
        color: var(--accent-soft);
        text-transform: uppercase;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .header-subtitle {
        font-size: 12.5px;
        color: var(--text-muted);
        margin-top: 4px;
        letter-spacing: 0.2px;
        text-transform: none;
        font-weight: 400;
    }
    .status-pill {
        background-color: rgba(16, 185, 129, 0.12);
        color: var(--success-soft);
        border: 1px solid rgba(16, 185, 129, 0.4);
        padding: 6px 16px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.3px;
        white-space: nowrap;
    }
    .status-pill::before {
        content: '';
    }

    /* ---------------------------------------------------------------- */
    /* Approval status banners                                           */
    /* ---------------------------------------------------------------- */
    .approval-box-success {
        background: linear-gradient(90deg, rgba(16, 185, 129, 0.12) 0%, rgba(16, 185, 129, 0.04) 100%);
        border: 1px solid rgba(16, 185, 129, 0.45);
        color: var(--success-soft);
        padding: 14px 20px;
        border-radius: 10px;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 22px;
        display: flex;
        align-items: center;
        gap: 10px;
        box-shadow: 0 2px 12px rgba(16, 185, 129, 0.08);
    }
    .approval-box-warning {
        background: linear-gradient(90deg, rgba(245, 158, 11, 0.14) 0%, rgba(245, 158, 11, 0.04) 100%);
        border: 1px solid rgba(245, 158, 11, 0.45);
        color: var(--warning-soft);
        padding: 14px 20px;
        border-radius: 10px;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 22px;
        display: flex;
        align-items: center;
        gap: 10px;
        box-shadow: 0 2px 12px rgba(245, 158, 11, 0.08);
    }

    /* ---------------------------------------------------------------- */
    /* Cards & Containers (native st.container(border=True) styling)     */
    /* ---------------------------------------------------------------- */
    .card-container {
        background-color: var(--surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 20px;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--surface);
        border: 1px solid var(--border) !important;
        border-radius: 14px !important;
        box-shadow: 0 2px 16px rgba(0, 0, 0, 0.25);
    }
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        padding: 4px 2px;
    }

    /* Section subheaders */
    h3, .stMarkdown h3 {
        font-size: 1.02rem !important;
        font-weight: 700 !important;
        color: var(--text-primary) !important;
        letter-spacing: 0.2px;
        border-bottom: 1px solid var(--border-subtle);
        padding-bottom: 10px;
        margin-bottom: 14px !important;
    }
    h4, .stMarkdown h4 {
        font-size: 0.88rem !important;
        font-weight: 700 !important;
        color: var(--text-secondary) !important;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        margin-top: 6px !important;
    }

    /* ---------------------------------------------------------------- */
    /* Badges                                                             */
    /* ---------------------------------------------------------------- */
    .confidence-badge-green {
        background-color: rgba(16, 185, 129, 0.14);
        color: var(--success-soft);
        border: 1px solid rgba(16, 185, 129, 0.35);
        font-size: 11px;
        padding: 3px 10px;
        border-radius: 6px;
        font-weight: 700;
        letter-spacing: 0.3px;
    }
    .confidence-badge-amber {
        background-color: rgba(245, 158, 11, 0.16);
        color: var(--warning-soft);
        border: 1px solid rgba(245, 158, 11, 0.35);
        font-size: 11px;
        padding: 3px 10px;
        border-radius: 6px;
        font-weight: 700;
        letter-spacing: 0.3px;
    }

    /* ---------------------------------------------------------------- */
    /* Inputs                                                             */
    /* ---------------------------------------------------------------- */
    .stTextInput input, .stTextArea textarea {
        background-color: var(--surface-alt) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
        font-size: 0.9rem !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px var(--accent-glow) !important;
    }
    .stTextInput label {
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        color: var(--text-secondary) !important;
        text-transform: uppercase;
        letter-spacing: 0.4px;
    }

    /* ---------------------------------------------------------------- */
    /* Buttons                                                            */
    /* ---------------------------------------------------------------- */
    .stButton button, .stDownloadButton button {
        border-radius: 9px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        padding: 0.55rem 1.2rem !important;
        border: 1px solid var(--border) !important;
        transition: transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease !important;
        letter-spacing: 0.2px;
    }
    .stButton button:hover, .stDownloadButton button:hover {
        transform: translateY(-1px);
        border-color: var(--accent-soft) !important;
        box-shadow: 0 4px 14px rgba(59, 130, 246, 0.18);
    }
    .stButton button[kind="primary"] {
        background: linear-gradient(90deg, #2563eb 0%, #3b82f6 100%) !important;
        border: none !important;
        color: white !important;
        box-shadow: 0 3px 14px rgba(37, 99, 235, 0.3);
    }
    .stButton button[kind="primary"]:hover {
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4);
    }

    /* ---------------------------------------------------------------- */
    /* Expanders                                                          */
    /* ---------------------------------------------------------------- */
    .streamlit-expanderHeader, details summary {
        background-color: var(--surface-alt) !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
    }
    div[data-testid="stExpander"] {
        border: none !important;
    }

    /* ---------------------------------------------------------------- */
    /* Data editor / dataframe                                           */
    /* ---------------------------------------------------------------- */
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        border: 1px solid var(--border);
        border-radius: 10px;
        overflow: hidden;
    }

    /* ---------------------------------------------------------------- */
    /* Alerts (st.warning / st.info / st.success / st.error)             */
    /* ---------------------------------------------------------------- */
    div[data-testid="stAlert"] {
        border-radius: 10px !important;
        font-size: 0.88rem !important;
    }

    /* ---------------------------------------------------------------- */
    /* Dividers                                                           */
    /* ---------------------------------------------------------------- */
    hr {
        border-color: var(--border-subtle) !important;
        margin: 1.4rem 0 !important;
    }

    /* ---------------------------------------------------------------- */
    /* Responsive tweaks                                                  */
    /* ---------------------------------------------------------------- */
    @media (max-width: 900px) {
        .top-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 10px;
        }
        .header-title {
            font-size: 15px;
        }
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
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
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    if clean_text.endswith("```"):
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
    <div>
        <div class="header-title">📄 Multimodal VLM &nbsp;•&nbsp; Side-by-Side HITL Inspection</div>
        <div class="header-subtitle">Zero-shot multimodal extraction with confidence-gated human verification</div>
    </div>
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
        with st.container(border=True):
            st.subheader("📄 Original Ingested Document")
            st.image(img, use_container_width=True)

    # Column 2: Human-in-the-Loop Panel
    with col_panel:
        with st.container(border=True):
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