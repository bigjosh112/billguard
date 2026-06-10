"""
Seed BillGuard with realistic Nigerian demo data.
Run this to populate the database for the hackathon demo.

Usage: python seed_demo.py
"""

import asyncio
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

from db import MongoDBClient


DEMO_TRANSACTIONS = [
    # === INCOME ===
    {"date": "2026-05-25", "description": "SALARY PAYMENT - VOYATEK GROUP", "amount": 450000, "type": "credit", "balance": 450000, "category": "income", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-04-25", "description": "SALARY PAYMENT - VOYATEK GROUP", "amount": 450000, "type": "credit", "balance": 380000, "category": "income", "bank": "GTBank", "currency": "NGN"},

    # === RENT ===
    {"date": "2026-05-01", "description": "TRANSFER TO LANDLORD PROPERTY MANAGEMENT", "amount": 120000, "type": "debit", "balance": 330000, "category": "rent", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-04-01", "description": "TRANSFER TO LANDLORD PROPERTY MANAGEMENT", "amount": 120000, "type": "debit", "balance": 260000, "category": "rent", "bank": "GTBank", "currency": "NGN"},

    # === LOAN ===
    {"date": "2026-05-15", "description": "RENMONEY LOAN REPAYMENT", "amount": 45000, "type": "debit", "balance": 285000, "category": "loan_savings", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-04-15", "description": "RENMONEY LOAN REPAYMENT", "amount": 45000, "type": "debit", "balance": 195000, "category": "loan_savings", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-05-20", "description": "PIGGYVEST SAVINGS TRANSFER", "amount": 20000, "type": "debit", "balance": 265000, "category": "loan_savings", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-04-20", "description": "PIGGYVEST SAVINGS TRANSFER", "amount": 20000, "type": "debit", "balance": 175000, "category": "loan_savings", "bank": "GTBank", "currency": "NGN"},

    # === UTILITIES ===
    {"date": "2026-05-03", "description": "EKEDC ELECTRICITY TOKEN PAYMENT", "amount": 15000, "type": "debit", "balance": 270000, "category": "utilities", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-05-08", "description": "MTN AIRTIME AND DATA SUBSCRIPTION", "amount": 8000, "type": "debit", "balance": 262000, "category": "utilities", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-05-04", "description": "DSTV MONTHLY SUBSCRIPTION AUTO-DEBIT", "amount": 24800, "type": "debit", "balance": 250000, "category": "utilities", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-04-04", "description": "DSTV MONTHLY SUBSCRIPTION AUTO-DEBIT", "amount": 24800, "type": "debit", "balance": 160000, "category": "utilities", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-05-01", "description": "SHOWMAX MONTHLY SUBSCRIPTION", "amount": 4200, "type": "debit", "balance": 246000, "category": "utilities", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-05-01", "description": "NETFLIX SUBSCRIPTION USD CHARGE", "amount": 7500, "type": "debit", "balance": 242000, "category": "utilities", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-05-01", "description": "SPOTIFY PREMIUM MONTHLY", "amount": 2300, "type": "debit", "balance": 240000, "category": "utilities", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-05-15", "description": "CHATGPT PLUS SUBSCRIPTION", "amount": 6500, "type": "debit", "balance": 180000, "category": "utilities", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-04-15", "description": "CHATGPT PLUS SUBSCRIPTION", "amount": 6500, "type": "debit", "balance": 100000, "category": "utilities", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-05-10", "description": "SPECTRANET INTERNET SUBSCRIPTION", "amount": 12000, "type": "debit", "balance": 228000, "category": "utilities", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-04-10", "description": "SPECTRANET INTERNET SUBSCRIPTION", "amount": 12000, "type": "debit", "balance": 88000, "category": "utilities", "bank": "GTBank", "currency": "NGN"},

    # === TRANSPORT ===
    {"date": "2026-05-06", "description": "UBER TRIP PAYMENT", "amount": 3200, "type": "debit", "balance": 224800, "category": "transport", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-05-09", "description": "UBER TRIP PAYMENT", "amount": 2800, "type": "debit", "balance": 222000, "category": "transport", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-05-12", "description": "TOTAL PETROL STATION ABULE-EGBA", "amount": 25000, "type": "debit", "balance": 197000, "category": "transport", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-05-19", "description": "TOTAL PETROL STATION ABULE-EGBA", "amount": 25000, "type": "debit", "balance": 172000, "category": "transport", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-04-18", "description": "CAR INSURANCE PREMIUM PAYMENT", "amount": 18000, "type": "debit", "balance": 72000, "category": "transport", "bank": "GTBank", "currency": "NGN"},

    # === FOOD ===
    {"date": "2026-05-07", "description": "SHOPRITE SURULERE PURCHASE", "amount": 18500, "type": "debit", "balance": 203500, "category": "food", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-05-14", "description": "JUSTRITE SUPERMARKET PURCHASE", "amount": 12300, "type": "debit", "balance": 185000, "category": "food", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-05-21", "description": "SHOPRITE SURULERE PURCHASE", "amount": 16800, "type": "debit", "balance": 155000, "category": "food", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-05-10", "description": "CHICKEN REPUBLIC MARYLAND", "amount": 4500, "type": "debit", "balance": 180500, "category": "food", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-05-16", "description": "DOMINOS PIZZA ORDER", "amount": 8900, "type": "debit", "balance": 163000, "category": "food", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-05-22", "description": "COLD STONE CREAMERY LEKKI", "amount": 5600, "type": "debit", "balance": 149400, "category": "food", "bank": "GTBank", "currency": "NGN"},

    # === ATM / CASH ===
    {"date": "2026-05-05", "description": "ATM WITHDRAWAL IKEJA BRANCH", "amount": 20000, "type": "debit", "balance": 225000, "category": "cash", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-05-18", "description": "ATM WITHDRAWAL MARYLAND", "amount": 15000, "type": "debit", "balance": 140000, "category": "cash", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-04-08", "description": "ATM WITHDRAWAL IKEJA BRANCH", "amount": 25000, "type": "debit", "balance": 135000, "category": "cash", "bank": "GTBank", "currency": "NGN"},

    # === SHOPPING / EDUCATION ===
    {"date": "2026-05-11", "description": "UDEMY COURSE PURCHASE", "amount": 12000, "type": "debit", "balance": 168000, "category": "education", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-05-20", "description": "CANVA PRO MONTHLY SUBSCRIPTION", "amount": 3500, "type": "debit", "balance": 152000, "category": "utilities", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-05-23", "description": "POS PURCHASE BALOGUN MARKET", "amount": 8200, "type": "debit", "balance": 144000, "category": "shopping", "bank": "GTBank", "currency": "NGN"},
    {"date": "2026-04-22", "description": "JUMIA ONLINE SHOPPING", "amount": 15600, "type": "debit", "balance": 64000, "category": "shopping", "bank": "GTBank", "currency": "NGN"},
]


def make_ref(date, desc, amount):
    return hashlib.md5(f"{date}|{desc}|{amount}".encode()).hexdigest()


for t in DEMO_TRANSACTIONS:
    t["reference"] = make_ref(t["date"], t["description"], t["amount"])


DEMO_BILLS = [
    {"name": "House Rent", "amount": 120000, "due_date": "2026-06-01", "category": "rent", "currency": "NGN"},
    {"name": "RenMoney Loan", "amount": 45000, "due_date": "2026-06-15", "category": "loan_savings", "currency": "NGN"},
    {"name": "EKEDC Electricity", "amount": 15000, "due_date": "2026-06-05", "category": "utilities", "currency": "NGN"},
    {"name": "Spectranet Internet", "amount": 12000, "due_date": "2026-06-10", "category": "utilities", "currency": "NGN"},
    {"name": "MTN Data", "amount": 8000, "due_date": "2026-06-08", "category": "utilities", "currency": "NGN"},
    {"name": "DSTV Subscription", "amount": 24800, "due_date": "2026-06-04", "category": "utilities", "currency": "NGN"},
    {"name": "Car Insurance", "amount": 18000, "due_date": "2026-06-18", "category": "transport", "currency": "NGN"},
    {"name": "Netflix", "amount": 7500, "due_date": "2026-06-01", "category": "utilities", "currency": "NGN"},
    {"name": "Spotify", "amount": 2300, "due_date": "2026-06-01", "category": "utilities", "currency": "NGN"},
    {"name": "ChatGPT Plus", "amount": 6500, "due_date": "2026-06-15", "category": "utilities", "currency": "NGN"},
    {"name": "Showmax", "amount": 4200, "due_date": "2026-06-01", "category": "utilities", "currency": "NGN"},
    {"name": "Canva Pro", "amount": 3500, "due_date": "2026-06-20", "category": "utilities", "currency": "NGN"},
    {"name": "PiggyVest Savings Target", "amount": 20000, "due_date": "2026-06-20", "category": "loan_savings", "currency": "NGN"},
]

DEMO_SALARY = {
    "amount": 450000,
    "pay_date": "2026-06-25",
    "currency": "NGN"
}


DEMO_SESSION = "demo_session"


async def seed():
    print("🌱 Seeding BillGuard demo data...")
    db = MongoDBClient()

    await db.transactions.delete_many({"session_id": DEMO_SESSION})
    await db.bills.delete_many({"session_id": DEMO_SESSION})
    await db.salary.delete_many({"session_id": DEMO_SESSION})
    await db.sessions.delete_many({"session_id": DEMO_SESSION})
    await db.forecasts.delete_many({"session_id": DEMO_SESSION})
    print(f"   ✓ Cleared demo session data ({DEMO_SESSION})")

    stored = await db.store_transactions(DEMO_TRANSACTIONS, DEMO_SESSION)
    print(f"   ✓ Stored {stored} transactions ({len(DEMO_TRANSACTIONS)} in seed data)")

    for bill in DEMO_BILLS:
        await db.store_bill(bill, DEMO_SESSION)
    print(f"   ✓ Stored {len(DEMO_BILLS)} upcoming bills")

    await db.store_salary(DEMO_SALARY, DEMO_SESSION)
    print("   ✓ Stored salary info (₦450,000 on 2026-06-25)")

    summary = await db.get_financial_summary(session_id=DEMO_SESSION)
    print(f"\n📊 Demo data summary:")
    print(f"   Total transactions: {summary['total_transactions_stored']}")
    print(f"   Last 30 days income:  ₦{summary['total_inflow']:,.0f}")
    print(f"   Last 30 days spending: ₦{summary['total_outflow']:,.0f}")
    print(f"   Net position:          ₦{summary['net']:,.0f}")
    print(f"   Upcoming bills:        {len(summary['upcoming_bills'])}")
    print(f"   Total bills due:       ₦{summary['total_bills_due']:,.0f}")
    print(f"\n✅ Demo data ready for session '{DEMO_SESSION}'!")
    print(f"   For demo video: run in browser console:")
    print(f"   localStorage.setItem('billguard_session_id', '{DEMO_SESSION}'); location.reload();")
    print(f"\n   Start the server with: uvicorn main:app --reload")


if __name__ == "__main__":
    asyncio.run(seed())
