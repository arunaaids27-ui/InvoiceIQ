"""
categorization/taxonomy.py

Standardized enterprise accounting taxonomy for invoice line items.
"""

EXPENSE_TAXONOMY = {
    "IT & Cloud Infrastructure": [
        "desktop", "computer", "laptop", "pc", "ram", "hardware", "software", 
        "cloud hosting", "server", "monitor", "windows", "dell", "hp", "macbook"
    ],
    "Office Supplies": [
        "stationery", "paper", "pen", "stapler", "printer ink", "toner", "desk accessories"
    ],
    "Logistics & Shipping": [
        "freight", "courier", "delivery charges", "packaging material", "postal charges", "shipping"
    ],
    "Meals & Entertainment": [
        "restaurant", "food", "beverages", "catering", "snacks", "lunch", "coffee"
    ],
    "Travel & Commute": [
        "fuel", "petrol", "diesel", "flight ticket", "hotel booking", "taxi", "train fare", "parking"
    ],
    "Utilities & Facilities": [
        "electricity", "water bill", "office rent", "internet broadband", "cleaning services"
    ],
    "Professional Services": [
        "legal fees", "audit charges", "consulting", "freelance services", "tax advisory"
    ]
}