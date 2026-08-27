"""
storage/db_manager.py

SQLite Storage Manager for InvoiceIQ.
"""

import sqlite3
import json
from typing import Dict, Any, List

DB_PATH = "invoices.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT,
            invoice_date TEXT,
            due_date TEXT,
            vendor_name TEXT,
            vendor_address TEXT,
            customer_name TEXT,
            customer_address TEXT,
            currency TEXT,
            subtotal REAL,
            tax REAL,
            total_amount REAL,
            overall_confidence INTEGER,
            review_status TEXT,
            raw_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS line_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER,
            description TEXT,
            quantity REAL,
            unit_price REAL,
            tax REAL,
            total REAL,
            assigned_category TEXT DEFAULT 'Uncategorized',
            FOREIGN KEY (invoice_id) REFERENCES invoices (id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


def save_invoice_record(invoice_data: Dict[str, Any], confidence_score: int, review_status: str) -> int:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO invoices (
            invoice_number, invoice_date, due_date, vendor_name,
            vendor_address, customer_name, customer_address, currency,
            subtotal, tax, total_amount, overall_confidence, review_status, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        invoice_data.get("invoice_number"),
        invoice_data.get("invoice_date"),
        invoice_data.get("due_date"),
        invoice_data.get("vendor_name"),
        invoice_data.get("vendor_address"),
        invoice_data.get("customer_name"),
        invoice_data.get("customer_address"),
        invoice_data.get("currency"),
        invoice_data.get("subtotal"),
        invoice_data.get("tax"),
        invoice_data.get("total_amount"),
        confidence_score,
        review_status,
        json.dumps(invoice_data, ensure_ascii=False)
    ))

    invoice_id = cursor.lastrowid

    # Correct category key extraction
    line_items = invoice_data.get("line_items") or []
    for item in line_items:
        if isinstance(item, dict):
            # Prioritize assigned_category from semantic categorizer
            cat = item.get("assigned_category") or item.get("category") or "Miscellaneous"
            
            cursor.execute("""
                INSERT INTO line_items (
                    invoice_id, description, quantity, unit_price, tax, total, assigned_category
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                invoice_id,
                item.get("description"),
                item.get("quantity"),
                item.get("unit_price"),
                item.get("tax"),
                item.get("total"),
                cat
            ))

    conn.commit()
    conn.close()
    return invoice_id


def get_all_invoices() -> List[Dict[str, Any]]:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invoices ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_line_items() -> List[Dict[str, Any]]:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.*, i.vendor_name, i.invoice_date 
        FROM line_items l
        JOIN invoices i ON l.invoice_id = i.id
        ORDER BY l.id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]