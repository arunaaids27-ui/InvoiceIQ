import streamlit as st
import tempfile
import os
import json
import pandas as pd
from PIL import Image
import fitz  # PyMuPDF

from storage.db_manager import save_invoice_record, get_all_invoices, get_all_line_items
from categorization.expense_categorizer import categorize_invoice_items
from vlm_extraction.invoice_extractor import extract_invoice_data
from confidence.confidence_scorer import (
    score_invoice_confidence,
    requires_manual_review,
    AUTO_APPROVE_THRESHOLD,
)

# ============================================================
# PAGE CONFIGURATION & ENTERPRISE DARK SAAS CSS
# ============================================================
st.set_page_config(
    page_title="InvoiceIQ Enterprise | Multimodal VLM",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"], .stMarkdown {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    
    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }

    .stApp {
        background: radial-gradient(circle at 50% 0%, #171E31 0%, #070A12 100%) !important;
        color: #F8FAFC !important;
    }

    section[data-testid="stSidebar"] {
        background-color: #0B0F19 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
        padding-top: 1rem !important;
    }

    .top-header-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.9rem 1.4rem;
        background: rgba(18, 24, 42, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35);
    }

    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.35);
        color: #34D399;
        padding: 5px 14px;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.03em;
    }

    .pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10B981;
        box-shadow: 0 0 10px #10B981;
    }

    .glass-card {
        background: rgba(18, 24, 42, 0.65);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        backdrop-filter: blur(10px);
    }

    .banner-high {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.18) 0%, rgba(5, 150, 105, 0.05) 100%);
        border: 1px solid rgba(16, 185, 129, 0.45);
        color: #34D399;
        padding: 14px 20px;
        border-radius: 14px;
        font-weight: 600;
        margin-bottom: 1.4rem;
    }

    .banner-mod {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.18) 0%, rgba(217, 119, 6, 0.05) 100%);
        border: 1px solid rgba(245, 158, 11, 0.45);
        color: #FBBF24;
        padding: 14px 20px;
        border-radius: 14px;
        font-weight: 600;
        margin-bottom: 1.4rem;
    }

    .banner-low {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.18) 0%, rgba(185, 28, 28, 0.05) 100%);
        border: 1px solid rgba(239, 68, 68, 0.45);
        color: #F87171;
        padding: 14px 20px;
        border-radius: 14px;
        font-weight: 600;
        margin-bottom: 1.4rem;
    }

    div[data-testid="stMetric"] {
        background: rgba(18, 24, 42, 0.75) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        padding: 16px 20px !important;
    }

    button[kind="primary"], .stDownloadButton>button {
        background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }

    /* 🟢 Green / ⚪ N/A / 🔴 Red Dynamic HITL Border Highlighting */
    .field-verified {
        border-left: 4px solid #10B981 !important;
        background: rgba(16, 185, 129, 0.08);
        padding: 6px 10px;
        border-radius: 6px;
        margin-bottom: 4px;
        font-size: 0.8rem;
    }

    .field-na {
        border-left: 4px solid #64748B !important;
        background: rgba(100, 116, 139, 0.08);
        padding: 6px 10px;
        border-radius: 6px;
        margin-bottom: 4px;
        font-size: 0.8rem;
    }

    .field-warning {
        border-left: 4px solid #EF4444 !important;
        background: rgba(239, 68, 68, 0.12);
        padding: 6px 10px;
        border-radius: 6px;
        margin-bottom: 4px;
        font-size: 0.8rem;
        animation: pulse-red 2s infinite;
    }

    @keyframes pulse-red {
        0%, 100% { box-shadow: 0 0 0px rgba(239, 68, 68, 0); }
        50% { box-shadow: 0 0 8px rgba(239, 68, 68, 0.35); }
    }
</style>
""", unsafe_allow_html=True)

# Helper function to get image preview from PDF or Image
def get_preview_image(uploaded_file):
    try:
        uploaded_file.seek(0)
        file_bytes = uploaded_file.read()
        if uploaded_file.name.lower().endswith(".pdf"):
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=150)
            return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        else:
            uploaded_file.seek(0)
            return Image.open(uploaded_file)
    except Exception:
        return None

# Session State Initialization
if "extracted_data" not in st.session_state: st.session_state["extracted_data"] = None
if "confidence_result" not in st.session_state: st.session_state["confidence_result"] = None
if "current_file_name" not in st.session_state: st.session_state["current_file_name"] = None
if "verified_data" not in st.session_state: st.session_state["verified_data"] = None

# Sidebar Ingestion
with st.sidebar:
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 1.2rem;">
            <div style="background: linear-gradient(135deg, #6366F1, #4F46E5); padding: 8px 12px; border-radius: 10px; font-weight: 800; font-size: 1.1rem; color: white;">⚡ IQ</div>
            <div>
                <div style="font-weight: 800; font-size: 1.05rem; color: #FFFFFF;">DocuFlow AI</div>
                <div style="font-size: 0.75rem; color: #64748B;">Multimodal AP Pipeline</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("##### 📁 DOCUMENT INGESTION")
    uploaded_file = st.file_uploader("Upload Invoice (PDF, PNG, JPG)", type=["pdf", "png", "jpg", "jpeg"], label_visibility="collapsed")
    st.markdown("---")
    st.markdown("##### 📑 RECENT RECORDS IN DB")
    recent_invoices = get_all_invoices()
    if recent_invoices:
        for inv in recent_invoices[:4]:
            stat_icon = "🟢" if "AUTO" in inv.get("review_status", "") else "🟠"
            st.markdown(f"**{inv.get('vendor_name') or 'Vendor'}** - `${inv.get('total_amount', 0)}` {stat_icon}")
    else:
        st.caption("No historical records found.")

# Main Header
st.markdown("""
<div class="top-header-bar">
    <span style="font-weight: 700; color: #818CF8;">MULTIMODAL VLM • SIDE-BY-SIDE HITL INSPECTION</span>
    <div class="status-pill"><div class="pulse-dot"></div> Pipeline Active</div>
</div>
""", unsafe_allow_html=True)

tab_extract, tab_analytics = st.tabs(["⚡ Document Extraction Studio", "📊 Spend Analytics & Audit Log"])

with tab_extract:
    if not uploaded_file:
        st.markdown("""
            <div class="glass-card" style="text-align: center; padding: 3.5rem 1rem;">
                <div style="font-size: 2.8rem; margin-bottom: 0.6rem;">📄</div>
                <div style="font-weight: 800; font-size: 1.2rem; color: #F8FAFC;">No Document Ingested</div>
                <div style="font-size: 0.88rem; color: #64748B; margin-top: 6px;">Upload an invoice from the sidebar to start side-by-side verification.</div>
            </div>
        """, unsafe_allow_html=True)
    else:
        if st.session_state["current_file_name"] != uploaded_file.name:
            st.session_state["current_file_name"] = uploaded_file.name
            st.session_state["extracted_data"] = None
            st.session_state["confidence_result"] = None
            st.session_state["verified_data"] = None

        if st.session_state["extracted_data"] is None:
            file_ext = os.path.splitext(uploaded_file.name)[1]
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
                    tmp.write(uploaded_file.getbuffer())
                    temp_path = tmp.name

                with st.spinner("🤖 Vision Model Extracting & Scoring Quality..."):
                    raw_data = extract_invoice_data(temp_path)
                    
                    # RAG Categorization
                    items = raw_data.get("line_items", [])
                    v_name = raw_data.get("vendor_name", "")
                    if items:
                        raw_data["line_items"] = categorize_invoice_items(items, v_name)
                    
                    st.session_state["extracted_data"] = raw_data
                    st.session_state["confidence_result"] = score_invoice_confidence(raw_data)
                    st.session_state["verified_data"] = raw_data
                st.success("✅ Extraction & Quality Verification Completed!")
            except Exception as e:
                st.error(f"❌ Error: {e}")
            finally:
                if temp_path and os.path.exists(temp_path): os.remove(temp_path)

        if st.session_state["extracted_data"] is not None:
            extracted_data = st.session_state["extracted_data"]
            confidence_result = st.session_state["confidence_result"]
            current_data = st.session_state.get("verified_data") or extracted_data
            review_info = requires_manual_review(confidence_result)

            score = confidence_result.get("overall_score", 0)
            tier = confidence_result.get("overall_tier", "LOW")

            if tier == "HIGH":
                st.markdown(f'<div class="banner-high">✅ <b>AUTO-APPROVED ({score}% Confidence):</b> Quality gate passed. Safe for direct accounting ingestion.</div>', unsafe_allow_html=True)
            elif tier == "MODERATE":
                st.markdown(f'<div class="banner-mod">⚠️ <b>HUMAN REVIEW REQUIRED ({score}% Confidence):</b> Inspect red-flagged fields against the source document.</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="banner-low">🚨 <b>CRITICAL REJECTION ({score}% Confidence):</b> Discrepancy detected. Mandatory verification required.</div>', unsafe_allow_html=True)

            # ============================================================
            # 🔍 SIDE-BY-SIDE DUAL PANE LAYOUT (ORIGINAL vs VERIFICATION FORM)
            # ============================================================
            col_doc_view, col_hitl_form = st.columns([1, 1.2], gap="large")

            # LEFT PANE: SOURCE DOCUMENT PREVIEW
            with col_doc_view:
                st.markdown("##### 📄 Original Ingested Document")
                preview_img = get_preview_image(uploaded_file)
                if preview_img:
                    st.image(preview_img, use_container_width=True, caption=f"Source: {uploaded_file.name}")
                else:
                    st.caption("Preview unavailable for this format.")

            # RIGHT PANE: FIELD STATUSES & EDITABLE FORM
            with col_hitl_form:
                st.markdown("##### ✏️ Human-in-the-Loop Verification")
                st.metric("Overall Extraction Confidence", f"{score}%", delta=confidence_result.get("overall_status", "LOW"))
                
                field_scores = confidence_result.get("field_scores", {})
                
                # Dynamic 3-State Label Checker (Green Verified / Grey N/A / Red Needs Review)
                def get_field_status(field_key):
                    f_info = field_scores.get(field_key, {})
                    status = f_info.get("status", "VERIFIED")
                    score_val = f_info.get("score", 0)
                    
                    if status in ["AUTO_ACCEPTED", "VERIFIED"]:
                        return "field-verified", f"🟢 Verified ({score_val}%)"
                    elif status in ["NOT_APPLICABLE", "NA"]:
                        return "field-na", "⚪ N/A (Not on Document)"
                    else:
                        return "field-warning", "🔴 Missing / Needs Review"

                def get_val(data, key): return "" if data.get(key) is None or str(data.get(key)).lower() in ["none", "null"] else str(data.get(key))

                with st.form(key="hitl_dual_pane_form"):
                    c1, t1 = get_field_status("vendor_name")
                    st.markdown(f'<div class="{c1}"><b>Vendor Name</b> • {t1}</div>', unsafe_allow_html=True)
                    v_vendor = st.text_input("Vendor", value=get_val(current_data, "vendor_name"), label_visibility="collapsed")

                    c2, t2 = get_field_status("invoice_number")
                    st.markdown(f'<div class="{c2}"><b>Invoice Number</b> • {t2}</div>', unsafe_allow_html=True)
                    v_inv_num = st.text_input("Invoice Num", value=get_val(current_data, "invoice_number"), label_visibility="collapsed")

                    c_d1, c_d2 = st.columns(2)
                    with c_d1:
                        c3, t3 = get_field_status("invoice_date")
                        st.markdown(f'<div class="{c3}"><b>Invoice Date</b> • {t3}</div>', unsafe_allow_html=True)
                        v_date = st.text_input("Date", value=get_val(current_data, "invoice_date"), label_visibility="collapsed")
                    with c_d2:
                        c4, t4 = get_field_status("due_date")
                        st.markdown(f'<div class="{c4}"><b>Due Date</b> • {t4}</div>', unsafe_allow_html=True)
                        v_due_date = st.text_input("Due Date", value=get_val(current_data, "due_date"), label_visibility="collapsed")

                    c_a1, c_a2 = st.columns(2)
                    with c_a1:
                        c5, t5 = get_field_status("tax")
                        st.markdown(f'<div class="{c5}"><b>Tax Amount</b> • {t5}</div>', unsafe_allow_html=True)
                        v_tax = st.text_input("Tax", value=get_val(current_data, "tax"), label_visibility="collapsed")
                    with c_a2:
                        c6, t6 = get_field_status("total_amount")
                        st.markdown(f'<div class="{c6}"><b>Total Amount</b> • {t6}</div>', unsafe_allow_html=True)
                        v_total = st.text_input("Total Amount", value=get_val(current_data, "total_amount"), label_visibility="collapsed")

                    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                    if st.form_submit_button("💾 Confirm & Commit Record to Database", type="primary", use_container_width=True):
                        verified_dict = dict(current_data)
                        verified_dict["vendor_name"] = v_vendor
                        verified_dict["invoice_number"] = v_inv_num
                        verified_dict["invoice_date"] = v_date
                        verified_dict["due_date"] = v_due_date
                        try: verified_dict["tax"] = float(v_tax)
                        except: verified_dict["tax"] = 0.0
                        try: verified_dict["total_amount"] = float(v_total)
                        except: verified_dict["total_amount"] = 0.0

                        verified_dict["line_items"] = current_data.get("line_items", [])
                        new_confidence = score_invoice_confidence(verified_dict)

                        st.session_state["verified_data"] = verified_dict
                        st.session_state["confidence_result"] = new_confidence
                        st.session_state["extracted_data"] = verified_dict

                        rev_status = "MANUALLY_CORRECTED" if review_info.get("needs_review") else "AUTO_VERIFIED"
                        saved_id = save_invoice_record(
                            invoice_data=verified_dict,
                            confidence_score=new_confidence["overall_score"],
                            review_status=rev_status
                        )
                        st.success(f"🎉 Verified Record #{saved_id} committed to Database!")
                        st.rerun()

            st.divider()

            # Line Items Table & RAG Match Inspector
            categorized_items = current_data.get("line_items", [])
            if categorized_items:
                st.markdown("##### 📦 Semantic Line-Item Taxonomy Routing")
                table_rows = [{
                    "#": i + 1,
                    "Description": itm.get("description", "-"),
                    "Qty": itm.get("quantity", 1),
                    "Unit Price": f"${itm.get('unit_price', 0)}",
                    "Total": f"${itm.get('total', 0)}",
                    "Category": f"🏷️ {itm.get('assigned_category', 'Miscellaneous')}",
                    "Cosine Match": f"{itm.get('category_confidence', 0)}%"
                } for i, itm in enumerate(categorized_items)]
                st.dataframe(table_rows, use_container_width=True)

                with st.expander("🧠 Inspect RAG Vector Matching (How AI Decided)"):
                    for idx, itm in enumerate(categorized_items, 1):
                        st.markdown(f"**Item #{idx}:** `{itm.get('description', '-')}`")
                        top_m = itm.get("rag_top_matches", [])
                        if top_m:
                            cols = st.columns(len(top_m))
                            for c_idx, match in enumerate(top_m):
                                with cols[c_idx]:
                                    rank_tag = "🥇 Top Match" if c_idx == 0 else f"🥈 Rank {c_idx+1}"
                                    border = "#10B981" if c_idx == 0 else "#475569"
                                    st.markdown(f"""
                                        <div style="border: 1px solid {border}; background: rgba(18,24,42,0.7); border-radius: 8px; padding: 8px 12px;">
                                            <div style="font-size: 0.7rem; color: #94A3B8;">{rank_tag}</div>
                                            <div style="font-size: 0.85rem; font-weight: 700; color: #F8FAFC;">{match['category']}</div>
                                            <div style="font-size: 0.75rem; color: #34D399; font-family: monospace;">Match: {match['score']}%</div>
                                        </div>
                                    """, unsafe_allow_html=True)

# TAB 2: ANALYTICS & AUDIT LOG
with tab_analytics:
    st.markdown("### 📊 Spend Analytics & Audit Log")
    all_invoices = get_all_invoices()
    all_items = get_all_line_items()

    if not all_invoices:
        st.info("No saved records found.")
    else:
        tot_count = len(all_invoices)
        tot_spend = sum(inv.get("total_amount") or 0.0 for inv in all_invoices)
        m1, m2 = st.columns(2)
        m1.metric("Processed Invoices", tot_count)
        m2.metric("Aggregated Spend", f"${tot_spend:,.2f}")

        if all_items:
            df_items = pd.DataFrame(all_items)
            if "assigned_category" in df_items.columns and "total" in df_items.columns:
                df_items["total"] = pd.to_numeric(df_items["total"], errors="coerce").fillna(0)
                cat_summary = df_items.groupby("assigned_category")["total"].sum().reset_index()
                cat_summary.columns = ["Expense Category", "Total Spend ($)"]
                st.bar_chart(data=cat_summary.sort_values(by="Total Spend ($)", ascending=True), x="Total Spend ($)", y="Expense Category", use_container_width=True)

        df_invoices = pd.DataFrame(all_invoices)[["id", "invoice_number", "vendor_name", "invoice_date", "total_amount", "overall_confidence", "review_status"]]
        st.dataframe(df_invoices, use_container_width=True)
        st.download_button(label="📥 Download Audit Ledger (CSV)", data=df_invoices.to_csv(index=False).encode('utf-8'), file_name="audit_ledger.csv", mime="text/csv", type="primary")