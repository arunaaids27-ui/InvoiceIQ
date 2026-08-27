"""
storage/seed_demo_data.py

Populates SQLite database with a realistic benchmark dataset of invoices
across multiple vendors and categories for live demonstration.
"""

from storage.db_manager import save_invoice_record, init_db
from categorization.expense_categorizer import categorize_invoice_items

SAMPLE_DATASET = [
    {
        "invoice_number": "INV-2026-001",
        "invoice_date": "2026-01-12",
        "due_date": "2026-02-12",
        "vendor_name": "Amazon Web Services (AWS)",
        "vendor_address": "410 Terry Ave N, Seattle, WA 98109",
        "customer_name": "InvoiceIQ Tech Corp",
        "customer_address": "100 Innovation Way, Suite 400",
        "currency": "$",
        "subtotal": 1450.00,
        "tax": 116.00,
        "total_amount": 1566.00,
        "confidence": 98,
        "status": "AUTO_VERIFIED",
        "line_items": [
            {"description": "EC2 Cloud Compute Instances Usage", "quantity": 1, "unit_price": 850.00, "total": 850.00},
            {"description": "Amazon S3 Standard Storage Subscription", "quantity": 1, "unit_price": 600.00, "total": 600.00}
        ]
    },
    {
        "invoice_number": "STP-88491",
        "invoice_date": "2026-01-18",
        "due_date": "2026-02-01",
        "vendor_name": "Staples Office Supplies",
        "vendor_address": "500 Staples Drive, Framingham, MA",
        "customer_name": "InvoiceIQ Tech Corp",
        "customer_address": "100 Innovation Way, Suite 400",
        "currency": "$",
        "subtotal": 340.50,
        "tax": 27.24,
        "total_amount": 367.74,
        "confidence": 96,
        "status": "AUTO_VERIFIED",
        "line_items": [
            {"description": "A4 Copier Paper 500 Sheets (Ream)", "quantity": 10, "unit_price": 12.50, "total": 125.00},
            {"description": "HP High Yield Black Toner Cartridge", "quantity": 2, "unit_price": 95.00, "total": 190.00},
            {"description": "Gel Ink Pens Box of 24", "quantity": 1, "unit_price": 25.50, "total": 25.50}
        ]
    },
    {
        "invoice_number": "FDX-993012",
        "invoice_date": "2026-01-25",
        "due_date": None,
        "vendor_name": "FedEx Logistics",
        "vendor_address": "942 South Shady Grove Road, Memphis, TN",
        "customer_name": "InvoiceIQ Tech Corp",
        "customer_address": "100 Innovation Way, Suite 400",
        "currency": "$",
        "subtotal": 520.00,
        "tax": 0.00,
        "total_amount": 520.00,
        "confidence": 88,
        "status": "MANUALLY_CORRECTED",
        "line_items": [
            {"description": "Priority Overnight Air Cargo Freight Delivery", "quantity": 1, "unit_price": 420.00, "total": 420.00},
            {"description": "Protective Shipping Packaging Material", "quantity": 1, "unit_price": 100.00, "total": 100.00}
        ]
    },
    {
        "invoice_number": "UBR-TRIP-741",
        "invoice_date": "2026-02-02",
        "due_date": "2026-02-02",
        "vendor_name": "Uber Business Rides",
        "vendor_address": "1455 Market St, San Francisco, CA",
        "customer_name": "Arun Kumar",
        "customer_address": "100 Innovation Way, Suite 400",
        "currency": "$",
        "subtotal": 185.00,
        "tax": 14.80,
        "total_amount": 199.80,
        "confidence": 99,
        "status": "AUTO_VERIFIED",
        "line_items": [
            {"description": "Airport to Client Office Taxi Cab Commute", "quantity": 1, "unit_price": 120.00, "total": 120.00},
            {"description": "Executive Commute Travel & Toll Charges", "quantity": 1, "unit_price": 65.00, "total": 65.00}
        ]
    },
    {
        "invoice_number": "DEL-CONS-301",
        "invoice_date": "2026-02-10",
        "due_date": "2026-03-10",
        "vendor_name": "Deloitte Advisory LLP",
        "vendor_address": "30 Rockefeller Plaza, New York, NY",
        "customer_name": "InvoiceIQ Tech Corp",
        "customer_address": "100 Innovation Way, Suite 400",
        "currency": "$",
        "subtotal": 3500.00,
        "tax": 280.00,
        "total_amount": 3780.00,
        "confidence": 95,
        "status": "AUTO_VERIFIED",
        "line_items": [
            {"description": "Quarterly Financial Audit & Tax Advisory", "quantity": 1, "unit_price": 3500.00, "total": 3500.00}
        ]
    },
    {
        "invoice_number": "SBUX-CAT-550",
        "invoice_date": "2026-02-14",
        "due_date": None,
        "vendor_name": "Starbucks Coffee & Catering",
        "vendor_address": "2401 Utah Ave S, Seattle, WA",
        "customer_name": "InvoiceIQ Tech Corp",
        "customer_address": "100 Innovation Way, Suite 400",
        "currency": "$",
        "subtotal": 245.00,
        "tax": 19.60,
        "total_amount": 264.60,
        "confidence": 84,
        "status": "MANUALLY_CORRECTED",
        "line_items": [
            {"description": "Corporate Team Meeting Beverages and Snacks", "quantity": 1, "unit_price": 145.00, "total": 145.00},
            {"description": "Client Lunch Food & Coffee Catering", "quantity": 1, "unit_price": 100.00, "total": 100.00}
        ]
    },
    {
        "invoice_number": "DELL-HW-9021",
        "invoice_date": "2026-02-16",
        "due_date": "2026-03-16",
        "vendor_name": "Dell Technologies",
        "vendor_address": "One Dell Way, Round Rock, TX",
        "customer_name": "InvoiceIQ Tech Corp",
        "customer_address": "100 Innovation Way, Suite 400",
        "currency": "$",
        "subtotal": 4200.00,
        "tax": 336.00,
        "total_amount": 4536.00,
        "confidence": 97,
        "status": "AUTO_VERIFIED",
        "line_items": [
            {"description": "Dell OptiPlex Desktop Computer PC 16GB RAM", "quantity": 3, "unit_price": 900.00, "total": 2700.00},
            {"description": "UltraSharp 27 inch 4K Monitors", "quantity": 3, "unit_price": 500.00, "total": 1500.00}
        ]
    }
]


def seed_dataset():
    """Seeds the SQLite database with benchmark demo invoices."""
    init_db()
    print("🚀 Seeding demo dataset into SQLite database...")

    for inv in SAMPLE_DATASET:
        # Run semantic categorization on line items
        cat_items = categorize_invoice_items(inv["line_items"], inv["vendor_name"])
        inv["line_items"] = cat_items

        inv_id = save_invoice_record(
            invoice_data=inv,
            confidence_score=inv["confidence"],
            review_status=inv["status"]
        )
        print(f"  ✅ Inserted Invoice #{inv['invoice_number']} (ID: {inv_id}) - Vendor: {inv['vendor_name']}")

    print("\n🎉 Demo dataset seeded successfully! Open Streamlit Analytics tab to view.")


if __name__ == "__main__":
    seed_dataset()