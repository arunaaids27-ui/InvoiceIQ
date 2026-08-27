# InvoiceIQ – Intelligent Invoice Processing & Expense Categorization

## 📌 Overview

**InvoiceIQ** is an AI-powered intelligent invoice processing and expense categorization system that automates the extraction, verification, and classification of information from invoices.

The system uses **Vision Language Models (VLMs)** to understand invoices with different layouts and extract important fields such as vendor name, invoice number, invoice date, total amount, and other relevant details. A **confidence scoring mechanism** evaluates the reliability of extracted information and identifies invoices that require manual verification.

The system further uses **Retrieval-Augmented Generation (RAG)** to classify expenses based on relevant contextual information, making the overall invoice processing workflow more intelligent and reliable.

---

## 🎯 Problem Statement

Traditional invoice processing systems often depend on fixed OCR templates and predefined layouts. This makes them less effective when invoices have:

* Different layouts and formats
* Multiple vendors
* Poor image quality
* Tables and complex structures
* Different invoice templates
* Indian GST invoice formats

Manual verification and expense categorization also require significant time and effort.

**InvoiceIQ** addresses these challenges by combining **VLM-based extraction, confidence scoring, human-in-the-loop verification, and RAG-based expense categorization** into a single system.

---

## 🚀 Key Features

### 1. 📄 Invoice Upload

* Supports invoice images and PDF documents.
* Provides a simple Streamlit-based interface.
* Handles multiple invoice formats.

### 2. 🔍 VLM-Based Invoice Extraction

Uses a Vision Language Model to understand the invoice visually and extract structured information.

Extracted fields include:

* Vendor Name
* Invoice Number
* Invoice Date
* Due Date
* Customer Name
* Customer Address
* Total Amount
* Other invoice-related information

Unlike traditional template-based extraction, the system is designed to work with invoices having different layouts.

### 3. 📊 Confidence Scoring

A rule-based confidence scoring module evaluates the reliability of extracted fields.

The system:

* Assigns confidence scores to individual fields.
* Identifies missing or low-confidence critical fields.
* Calculates an overall invoice confidence score.
* Determines whether manual verification is required.

### 4. 👤 Human-in-the-Loop Verification

When extracted information has low confidence, the system automatically triggers a manual verification step.

Users can review and edit the extracted invoice information before continuing with further processing.

### 5. 🧠 RAG-Based Expense Categorization

The system uses **Retrieval-Augmented Generation (RAG)** to provide contextual information for expense classification.

Instead of relying only on predefined rules, relevant knowledge is retrieved and provided to the language model to improve expense categorization.

### 6. 📈 Interactive Dashboard

A Streamlit dashboard provides:

* Invoice details
* Extracted fields
* Confidence scores
* Manual verification alerts
* Expense category
* Processing results

---

## 🔄 System Workflow

```text
                Invoice Upload
                      ↓
              Preprocessing
                      ↓
          VLM-Based Extraction
                      ↓
             Structured Data
                      ↓
             Confidence Scoring
                      ↓
             ┌───────────────┐
             │ Low Confidence?│
             └───────┬───────┘
                 Yes ↓     ↓ No
          Manual Verification
                 ↓         ↓
                 └────┬────┘
                      ↓
                 RAG Retrieval
                      ↓
            Expense Categorization
                      ↓
                Final Results
                      ↓
               Streamlit UI
```

---

## 🏗️ Project Architecture

```text
InvoiceIQ/
│
├── app.py
│
├── preprocessing/
│   └── invoice_preprocessor.py
│
├── vlm_extraction/
│   ├── prompts.py
│   ├── vlm_client.py
│   └── invoice_extractor.py
│
├── confidence/
│   └── confidence_scorer.py
│
├── rag/
│   └── ...
│
├── classification/
│   └── ...
│
├── sample_invoice.jpg
│
├── .env
├── .gitignore
└── README.md
```

---

## 🛠️ Technology Stack

| Component               | Technology              |
| ----------------------- | ----------------------- |
| Programming Language    | Python                  |
| Frontend / UI           | Streamlit               |
| Invoice Processing      | PyMuPDF, Pillow         |
| AI Model                | Vision Language Model   |
| LLM Integration         | Google GenAI            |
| Confidence Scoring      | Rule-Based Scoring      |
| Knowledge Retrieval     | RAG                     |
| Expense Classification  | LLM + Retrieved Context |
| Development Environment | VS Code                 |

---

## 🧩 Major Modules

### Preprocessing

Converts uploaded PDF and image invoices into suitable image representations for downstream AI processing.

### VLM Extraction

Processes invoice images using a Vision Language Model and converts unstructured invoice information into structured JSON data.

### Confidence Scoring

Evaluates the extracted fields and calculates field-level and invoice-level confidence.

Critical fields include:

```text
invoice_number
invoice_date
vendor_name
total_amount
```

### Manual Verification

Invoices containing low-confidence information are flagged for human review.

### RAG

Retrieves relevant information from the knowledge base and provides contextual information for expense categorization.

### Expense Classification

Uses the extracted invoice information and retrieved context to determine the appropriate expense category.

---

## 🔐 Environment Setup

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_api_key_here
```

**Important:** Never commit your API key to GitHub.

Make sure `.env` is included in `.gitignore`.

---

## ⚙️ Installation

Clone the repository:

```bash
git clone https://github.com/your-username/InvoiceIQ.git
cd InvoiceIQ
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate the environment.

### Windows

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
streamlit run app.py
```

The application will open in your browser.

---

## 📌 Project Objectives

* Automate invoice information extraction.
* Reduce dependency on fixed invoice templates.
* Improve reliability using confidence scoring.
* Introduce human verification for uncertain results.
* Automate expense categorization using RAG.
* Provide a simple and interactive invoice processing dashboard.
* Reduce manual effort in corporate expense management.

---

## 🔮 Future Enhancements

* Bulk invoice processing
* Asynchronous invoice processing using task queues
* Advanced table and line-item extraction
* Support for multilingual and bilingual invoices
* Improved Indian GST invoice understanding
* Database integration
* Expense analytics and reporting
* Role-based user authentication
* Automated financial reports
* Integration with enterprise accounting systems

---

## 🌟 Why InvoiceIQ?

InvoiceIQ combines multiple AI capabilities into one invoice-processing pipeline:

**Computer Vision + VLM + Confidence Scoring + Human Verification + RAG + Expense Classification**

This makes the system more flexible than traditional rule-based or template-dependent invoice processing solutions.

---

## 👩‍💻 Project Status

🚧 **Currently under development**

### Completed

* [x] Invoice Upload
* [x] PDF/Image Preprocessing
* [x] VLM-Based Invoice Extraction
* [x] Streamlit Integration
* [x] Confidence Scoring
* [x] Manual Verification Workflow

### In Progress

* [ ] RAG Pipeline
* [ ] Expense Classification
* [ ] Final Dashboard
* [ ] Bulk Invoice Processing

---

## 📜 License

This project is developed for academic and educational purposes.
