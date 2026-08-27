# 📄 InvoiceIQ: Multimodal Financial Document Extraction Engine

An intelligent document extraction and verification pipeline powered by Gemini Multimodal Vision models (`gemini-3.6-flash`). It processes PDFs and images of invoices to extract key structured financial fields deterministically.

---

## ✨ Key Features

- **Multimodal Visual Parsing**: Direct extraction from single/multi-page PDFs and low-resolution invoice images without OCR templates.
- **Configurable Extraction Schema**: Flexible parsing for core target fields (`invoice_number`, `invoice_date`, `vendor_name`, `tax_amount`, `total_amount`, and itemized `line_items`).
- **Automated Batch Processing**: Batch ingestion pipeline that traverses entire document datasets and exports unified JSON outputs.
- **Strict JSON Output**: Deterministic schema validation ready for database ingestion and downstream ERP systems.
- **Interactive Streamlit Web Dashboard**: File upload, real-time extraction preview, and instant CSV/JSON exports.

---

## 🛠️ Tech Stack

- **Core**: Python 3.10+
- **VLM Engine**: Google GenAI SDK (`gemini-3.6-flash`)
- **Document Preprocessing**: PyMuPDF (`fitz`), Pillow (PIL)
- **UI & Analytics**: Streamlit, Pandas
- **Config Management**: Python-dotenv

---

## 🚀 Setup & Execution

### 1. Clone Repository & Setup Virtual Environment
```bash
git clone [https://github.com/arunaaids27-ui/InvoiceIQ.git](https://github.com/arunaaids27-ui/InvoiceIQ.git)
cd InvoiceIQ
python -m venv venv
# Activate virtual environment (Windows):
.\venv\Scripts\activate