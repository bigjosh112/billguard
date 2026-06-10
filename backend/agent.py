"""
BillGuard Agent — Gemini-powered multi-step financial reasoning agent.

The agent has 8 tools, all backed by MongoDB:
1. get_financial_summary   — full picture of income vs spending
2. get_transactions        — query specific transaction categories
3. get_bills               — fetch upcoming bills
4. get_salary_info         — get salary/payday info
5. prioritise_bills        — run the priority algorithm and forecast
6. save_bill_from_chat     — save a bill the user mentions in chat
7. save_salary_from_chat   — save salary info from chat
8. get_spending_insights   — recurring charges from uploaded statements
9. mark_bill_paid_from_chat — mark a bill paid when user says they paid it
10. draft_negotiation_message — draft landlord/lender negotiation messages

Each tool call is visible to the user as a reasoning step.
"""

import os
import re
import json
import asyncio
from calendar import monthrange
from collections import defaultdict
from datetime import datetime
from typing import AsyncIterator
import google.generativeai as genai

from db import MongoDBClient

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


SYSTEM_PROMPT = """ABSOLUTE RULE — NEVER LIE ABOUT MONEY:
Before saying salary "covers" bills, ALWAYS verify:
  if salary < total_bills → salary does NOT cover bills
  Gap = total_bills - (current_balance + salary)
  If gap > 0 → there is a REAL SHORTFALL — state it honestly

NEVER say "salary covers the rest" unless (current_balance + salary) >= total_bills.
NEVER give false comfort. Wrong maths destroys trust.

When user asks "how do I sort the bills from the little I am expecting":
- "The little" = their salary amount
- Compare salary to total_bills FIRST
- If salary < total_bills → acknowledge this BEFORE any plan
- Then show what salary CAN realistically pay in priority order

WHEN SALARY < TOTAL BILLS, the response must:
1. State the shortfall clearly with percentage covered
2. Show exactly what salary CAN pay (priority order) — full, partial, cannot pay
3. Give specific negotiation strategies for each unpayable bill
4. Suggest Nigerian emergency cash options (Carbon, FairMoney, employer advance)

You are BillGuard — a warm, sharp, no-nonsense AI finance agent for Nigerian professionals.

You speak like a knowledgeable friend who understands money stress. Not a bank robot. Not a formal advisor.
A smart friend who has seen your account statement and genuinely wants to help you survive the month.

═══════════════════════════════════
PERSONALITY
═══════════════════════════════════
- Warm but direct. No corporate speak.
- You understand Nigerian financial reality: EKEDC bills, Renmoney loans, PiggyVest, DSTV, fuel costs, Lagos rent.
- When someone is stressed about money, you feel it and you help them fix it — step by step.
- Short sentences. Clear numbers. Real advice.
- Never say "Great question!" or "Certainly!" or "I'd be happy to help!"
- Never repeat yourself. Every response moves forward.

═══════════════════════════════════
CRITICAL RULE — EXTRACT AND SAVE IMMEDIATELY
═══════════════════════════════════
When a user mentions ANY bill, payment, expense, or salary in their message — extract it and save it to
MongoDB RIGHT AWAY using the tools.

Examples of what to extract:

"rent is 120,000"
→ call save_bill_from_chat: name="House Rent", amount=120000, category="rent",
  due_date = first of next month

"data - 25000"
→ call save_bill_from_chat: name="Data Subscription", amount=25000, category="utilities",
  due_date = reasonable near future date

"debts - 1800000"
→ call save_bill_from_chat: name="Debt Payment", amount=1800000, category="loan_savings",
  due_date = end of month

"my salary is 530000"
→ call save_salary_from_chat: amount=530000, pay_date = 25th of current or next month
  (use your best judgment on the date)

"I have bills - date - 200,000 data - 25000, debts - 1800000, others 300,000, rent - 1500000
and my salary is 530000"
→ Extract ALL of these and call save_bill_from_chat FIVE TIMES plus save_salary_from_chat ONCE.
  Save every single one.

For due dates: if not specified, use intelligent defaults:
- rent → 1st of next month
- utilities (data, electricity, internet) → 10th of month
- loans/debts → 15th of month
- subscriptions → 1st of month
- others → end of month

NEVER respond with "₦0 in bills due" if the user just told you about bills. Save them first, then analyse.

═══════════════════════════════════
TOOL CALLING ORDER
═══════════════════════════════════
1. If user mentions bills or salary → save them FIRST (save_bill_from_chat, save_salary_from_chat)
2. Then get fresh data to confirm what was saved (get_financial_summary or get_bills)
3. Then give your analysis based on fresh data

═══════════════════════════════════
RESPONSE FORMAT
═══════════════════════════════════
After saving bills, respond like this:

"Got it — saved [X] bills:
- House Rent — ₦1,500,000 (due June 1)
- DSTV — ₦25,000 (due June 10)
- Debt Payment — ₦1,800,000 (due June 15)
- Data — ₦25,000 (due June 10)
- Other — ₦300,000 (due June 30)

Salary: ₦530,000 saved.

Total bills: ₦3,650,000
Your salary covers only ₦530,000 of that (14.6%) — NOT the rest.

Gap after salary: ₦3,120,000 — negotiation and extra income required.
What's your current account balance? I'll build your priority payment plan."

═══════════════════════════════════
MONEY FORMATTING
═══════════════════════════════════
Always format: ₦1,500,000 not ₦1500000
Always use commas. Always use ₦ symbol.

═══════════════════════════════════
BILL PRIORITY (highest to lowest consequence)
═══════════════════════════════════
1. Rent — eviction risk
2. Loan/Debt repayments — penalties, credit damage
3. Electricity — power cut
4. Internet/Data — work disruption
5. Transport/Fuel — can't get to work
6. Food — critical
7. Subscriptions (DSTV, Netflix etc) — pause these first

═══════════════════════════════════
WHAT NOT TO DO
═══════════════════════════════════
- Never give the same response twice
- Never say bills are ₦0 when user just listed bills
- Never ignore information the user typed
- Never be formal or stiff
- Never ask for information the user already gave you
- Never give generic advice like "create a budget"

═══════════════════════════════════
CRITICAL — NEVER confuse these
═══════════════════════════════════
- Account balance = how much is in the bank RIGHT NOW
  → Do NOT save as a bill
  → Use in prioritise_bills tool when user asks what to pay
  → Phrases: "current balance is X", "balance is X", "I have X in my account"

- Bill/expense = money that needs to be paid OUT
  → Save with save_bill_from_chat
  → Must be explicitly labelled: "rent is X", "loan is X", "data - X"

- Salary = recurring income
  → Save with save_salary_from_chat

When user says "current balance is 20000 and salary is 530000":
CORRECT behavior:
  1. Call save_salary_from_chat with amount=530000
  2. Note current balance = ₦20,000 (NEVER save as a bill)
  3. Call prioritise_bills with current_balance=20000
  4. Give the full payment plan based on ₦20,000 available

═══════════════════════════════════
MATHS RULE — Always verify before stating
═══════════════════════════════════
- If total_bills > salary → "Your salary does NOT cover all bills. Gap of ₦X,XXX,XXX"
- If total_bills > current_balance → "You cannot cover all bills with your current balance"
- Never say "salary covers all bills" unless salary >= total_bills is mathematically true
- Always show the actual calculation:
  "₦530,000 salary − ₦3,875,000 bills = −₦3,345,000 gap"

═══════════════════════════════════
MEMORY RULE
═══════════════════════════════════
- When user gives you their balance in the conversation, USE IT IMMEDIATELY. Do not ask again.
- When user gives you salary, USE IT. Do not ask again.
- Read the full conversation history before asking for any information.
- If you already have balance + bills, run prioritisation immediately without asking again.

═══════════════════════════════════
RESPONSE QUALITY RULES
═══════════════════════════════════
1. Always show the maths explicitly
2. If the situation is bad, say so directly but with empathy — not cheerfully
3. Give ranked actions the user can take TODAY
4. If bills exceed salary, say so and suggest negotiation strategies
5. Offer to help draft negotiation messages to landlords or lenders
6. End with one specific next step or question
7. Never end with vague encouragement
8. Minimum response length for financial analysis: 8-10 lines. Never give a 2-line answer to a complex situation.

═══════════════════════════════════
WHEN USER SAYS THEY PAID A BILL
═══════════════════════════════════
"I paid rent", "just paid DSTV", "loan is done", "paid the electricity"
→ call mark_bill_paid_from_chat immediately, then recalculate their situation.

After marking paid, respond:
"Done — House Rent ₦1,500,000 crossed off.
Remaining bills: ₦2,395,000
You have ₦X left after that payment.
Next due: [next closest bill and date]"

This keeps the conversation moving forward with updated numbers every time something changes.

═══════════════════════════════════
NIGERIAN EMERGENCY CASH OPTIONS
═══════════════════════════════════
When crisis_level is "critical", ALWAYS mention these:

Salary Advance Apps (if employed):
- Carbon (getcarbon.co) — instant salary advance
- FairMoney — quick loans
- Branch — instant loans
- PalmCredit — quick loans
- Employer HR — ask for salary advance directly

If user is a developer/freelancer:
- Toptal, Upwork — take urgent gig
- Fiverr — offer quick service
- Ask existing clients for advance payment

Family/Network:
- Be direct about asking family for short-term help
- Offer to pay back with next salary

Frame as: "While you negotiate with creditors, here are ways to close the ₦X gap before [pay date]..."

═══════════════════════════════════
CRITICAL RESPONSE STRUCTURE (salary < total bills)
═══════════════════════════════════
When user asks to sort bills from salary and crisis_level = "critical":

**The honest picture:**
Your salary of ₦X covers only Y% of your ₦Z in bills. You're short by ₦GAP.

**Pay in full (₦X total):**
✅ [Bill] — ₦X (due [date]) — pay this first

**Partial payment:**
⚠️ House Rent — put ₦X toward ₦1,500,000 (₦X remaining — needs negotiation)

**Cannot pay this month — negotiate:**
❌ Debt Payment ₦1,800,000 → Call lender, ask for 1-month extension

**After paying what you can:**
Balance remaining: ₦X (keep for transport and food)

**To close the gap, also consider:**
- Salary advance from employer (ask HR)
- Carbon or FairMoney for emergency bridge loan
- Trusted family member — repay from next salary

**Want me to draft your message to the landlord or lender? Just say which one.**

Always end with one concrete next action. Never vague encouragement.
"""


TOOLS = [
    {
        "name": "get_financial_summary",
        "description": "Get a complete financial summary: total income, total spending by category, net position, and upcoming bills. Always call this first to get the full picture.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_transactions",
        "description": "Get individual transactions, optionally filtered by category (rent, transport, food, utilities, loan_savings, income, transfer, cash, healthcare, education, shopping, other).",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by category. Leave empty for all transactions."
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of transactions to return. Default 30."
                }
            },
            "required": []
        }
    },
    {
        "name": "get_bills",
        "description": "Get all upcoming unpaid bills with their due dates, amounts, and categories.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_salary_info",
        "description": "Get the user's salary amount and next pay date for cash flow forecasting.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "prioritise_bills",
        "description": "Run the bill prioritisation algorithm. Given current cash position, salary date, and all upcoming bills, calculate which bills to pay first, which can wait, and whether a shortfall exists.",
        "parameters": {
            "type": "object",
            "properties": {
                "current_balance": {
                    "type": "number",
                    "description": "User's current account balance in NGN. Use the amount the user stated in chat."
                }
            },
            "required": ["current_balance"]
        }
    },
    {
        "name": "save_bill_from_chat",
        "description": """Save a bill the user mentioned in chat.

CALL THIS whenever the user mentions any payment, bill, expense, or debt they need to make — even if they didn't give a due date. Infer a reasonable due date if not given:
- rent → 1st of next month
- utilities → 10th of current/next month
- loans → 15th of current/next month
- subscriptions → 1st of current/next month
- others → last day of current month

Call this MULTIPLE TIMES if user mentions multiple bills.
Extract every bill from the user's message.""",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Bill name e.g. 'House Rent', 'DSTV', 'Renmoney Loan'"
                },
                "amount": {
                    "type": "number",
                    "description": "Amount in NGN"
                },
                "due_date": {
                    "type": "string",
                    "description": "Due date in YYYY-MM-DD format. Infer if not given."
                },
                "category": {
                    "type": "string",
                    "description": "One of: rent, loan_savings, utilities, transport, food, healthcare, education, shopping, other"
                }
            },
            "required": ["name", "amount", "due_date", "category"]
        }
    },
    {
        "name": "save_salary_from_chat",
        "description": """Save the user's salary when they mention it in chat.
Use when user says 'I earn X', 'my salary is X', 'I get paid X on the Nth'.
If pay date is not given, default to the 25th of the current or next month.""",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "Monthly salary in NGN"
                },
                "pay_date": {
                    "type": "string",
                    "description": "Next pay date in YYYY-MM-DD format"
                }
            },
            "required": ["amount", "pay_date"]
        }
    },
    {
        "name": "get_spending_insights",
        "description": (
            "Analyse spending patterns over time from stored transaction history. "
            "Shows trends, identifies recurring charges, compares month over month. "
            "Only useful if user has uploaded a bank statement."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "mark_bill_paid_from_chat",
        "description": (
            "Mark a bill as paid when the user mentions they paid it. Use when user says things like "
            "'I paid rent', 'just paid my DSTV', 'loan payment done', 'crossed off the electricity bill'. "
            "Find the bill by name and mark it paid in MongoDB."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "bill_name": {
                    "type": "string",
                    "description": "Name of the bill to mark as paid",
                }
            },
            "required": ["bill_name"],
        }
    },
    {
        "name": "draft_negotiation_message",
        "description": (
            "Draft a professional negotiation message to a landlord or lender when the user "
            "cannot afford full payment. Use when user asks for help writing to their landlord, "
            "lender, or creditor."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "creditor_type": {
                    "type": "string",
                    "description": "One of: landlord, lender, other",
                },
                "bill_name": {
                    "type": "string",
                    "description": "e.g. house rent, Renmoney loan",
                },
                "amount_owed": {
                    "type": "number",
                    "description": "Total amount owed in NGN",
                },
                "amount_can_pay": {
                    "type": "number",
                    "description": "Amount user can pay now in NGN",
                },
                "reason": {
                    "type": "string",
                    "description": "e.g. cash flow issues this month",
                },
                "pay_remaining_by": {
                    "type": "string",
                    "description": "Date when they can pay the rest",
                },
            },
            "required": ["creditor_type", "bill_name", "amount_owed", "amount_can_pay"],
        }
    },
]

# Bill category priority: rent=1, loan=2, utilities=3, transport=4, food=5, subscriptions=6
BILL_CATEGORY_PRIORITY = {
    "rent": 1,
    "loan": 2,
    "loan_savings": 2,
    "utilities": 3,
    "transport": 4,
    "food": 5,
    "subscriptions": 6,
    "subscription": 6,
}

# Labels users type in chat → (display name, category)
BILL_KEYWORDS = {
    "rent": ("House Rent", "rent"),
    "data": ("Data Subscription", "utilities"),
    "date": ("Data Subscription", "utilities"),
    "internet": ("Internet", "utilities"),
    "electricity": ("Electricity", "utilities"),
    "electric": ("Electricity", "utilities"),
    "light": ("Electricity", "utilities"),
    "debts": ("Debt Payment", "loan_savings"),
    "debt": ("Debt Payment", "loan_savings"),
    "loan": ("Loan Repayment", "loan_savings"),
    "loans": ("Loan Repayment", "loan_savings"),
    "others": ("Other Expenses", "other"),
    "other": ("Other Expenses", "other"),
    "dstv": ("DSTV", "utilities"),
    "netflix": ("Netflix", "utilities"),
    "spotify": ("Spotify", "utilities"),
    "showmax": ("Showmax", "utilities"),
    "mtn": ("MTN Data", "utilities"),
    "spectranet": ("Spectranet Internet", "utilities"),
    "insurance": ("Insurance", "transport"),
    "food": ("Food", "food"),
    "renmoney": ("Renmoney Loan", "loan_savings"),
}


class BillGuardAgent:
    def __init__(self, db: MongoDBClient):
        self.db = db
        self._current_session_id = "default"
        self.model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT,
            tools=self._build_tools(),
        )

    def _build_tools(self):
        """Convert tool definitions to Gemini tool format."""
        from google.generativeai.types import Tool, FunctionDeclaration
        declarations = []
        for tool in TOOLS:
            declarations.append(FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters=tool["parameters"],
            ))
        return [Tool(function_declarations=declarations)]

    async def _execute_tool(self, name: str, args: dict) -> dict:
        """Execute a tool call and return the result."""
        sid = self._current_session_id
        try:
            if name == "get_financial_summary":
                return await self.db.get_financial_summary(session_id=sid)

            elif name == "get_transactions":
                category = args.get("category")
                limit = args.get("limit", 30)
                txns = await self.db.get_transactions(
                    limit=limit, category=category, session_id=sid
                )
                return {"transactions": txns, "count": len(txns)}

            elif name == "get_bills":
                bills = await self.db.get_bills(session_id=sid)
                return {"bills": bills, "total_bills": len(bills)}

            elif name == "get_salary_info":
                salary = await self.db.get_salary(session_id=sid)
                if not salary:
                    return {"error": "No salary info found. Ask user to provide salary amount and pay date."}
                return salary

            elif name == "prioritise_bills":
                return await self._run_prioritisation(
                    args.get("current_balance", 0), session_id=sid
                )

            elif name == "save_bill_from_chat":
                bill_data = {
                    "name": args.get("name"),
                    "amount": float(args.get("amount", 0)),
                    "due_date": args.get("due_date"),
                    "category": args.get("category", "other"),
                    "currency": "NGN",
                    "paid": False,
                }
                bill_id = await self.db.store_bill(bill_data, session_id=sid)
                return {
                    "saved": True,
                    "bill_id": bill_id,
                    "message": (
                        f"Saved: {bill_data['name']} — ₦{bill_data['amount']:,.0f} "
                        f"due {bill_data['due_date']}"
                    ),
                }

            elif name == "save_salary_from_chat":
                salary_data = {
                    "amount": float(args.get("amount", 0)),
                    "pay_date": args.get("pay_date"),
                    "currency": "NGN",
                }
                await self.db.store_salary(salary_data, session_id=sid)
                return {
                    "saved": True,
                    "message": (
                        f"Saved salary: ₦{salary_data['amount']:,.0f} "
                        f"on {salary_data['pay_date']}"
                    ),
                }

            elif name == "get_spending_insights":
                txns = await self.db.get_transactions(limit=200, session_id=sid)
                if not txns:
                    return {"error": "No transaction history. Upload a bank statement first."}

                recurring: dict[str, list[float]] = defaultdict(list)
                for t in txns:
                    if t.get("type") == "debit":
                        key = t["description"][:30].lower().strip()
                        recurring[key].append(t["amount"])

                subscriptions = []
                for desc, amounts in recurring.items():
                    if len(amounts) >= 2:
                        avg = sum(amounts) / len(amounts)
                        subscriptions.append({
                            "name": desc,
                            "avg_amount": round(avg, 2),
                            "occurrences": len(amounts),
                            "monthly_cost": round(avg, 2),
                        })

                subscriptions.sort(key=lambda x: x["avg_amount"], reverse=True)
                total_recurring = sum(s["monthly_cost"] for s in subscriptions)

                return {
                    "recurring_charges": subscriptions[:10],
                    "total_monthly_recurring": round(total_recurring, 2),
                    "total_transactions_analysed": len(txns),
                    "insight": (
                        f"Found {len(subscriptions)} recurring charges "
                        f"totalling ₦{total_recurring:,.0f}/month"
                    ),
                }

            elif name == "mark_bill_paid_from_chat":
                bill_name = args.get("bill_name", "").lower()
                bills = await self.db.get_bills(session_id=sid)
                matched = None
                for bill in bills:
                    if (
                        bill_name in bill["name"].lower()
                        or bill["name"].lower() in bill_name
                    ):
                        matched = bill
                        break

                if not matched:
                    return {
                        "error": (
                            f"Couldn't find a bill matching '{bill_name}'. "
                            f"Bills on file: {', '.join(b['name'] for b in bills)}"
                        )
                    }

                await self.db.mark_bill_paid(matched["_id"], session_id=sid)
                return {
                    "success": True,
                    "message": (
                        f"✓ {matched['name']} — ₦{matched['amount']:,.0f} marked as paid"
                    ),
                    "bill_name": matched["name"],
                    "amount": matched["amount"],
                }

            elif name == "draft_negotiation_message":
                creditor_type = args.get("creditor_type", "other")
                bill_name = args.get("bill_name", "payment")
                amount_owed = float(args.get("amount_owed", 0))
                amount_can_pay = float(args.get("amount_can_pay", 0))
                pay_remaining_by = args.get("pay_remaining_by", "end of month")
                reason = args.get("reason", "temporary cash flow constraints this month")

                if creditor_type == "landlord":
                    opening = "Dear Landlord/Property Manager,"
                    relationship = "your tenant"
                    commitment = "I value my tenancy and have always maintained payments"
                elif creditor_type == "lender":
                    opening = "Dear Loan Officer/Customer Service,"
                    relationship = "your customer"
                    commitment = "I have a good repayment history with your institution"
                else:
                    opening = "Dear Sir/Ma,"
                    relationship = "your customer"
                    commitment = "I have maintained a good relationship with your business"

                remaining = max(0, amount_owed - amount_can_pay)
                message = f"""{opening}

I am writing to respectfully request a brief payment arrangement for my {bill_name}.

The total amount due is ₦{amount_owed:,.0f}.
Due to {reason}, I am able to make an immediate payment of
₦{amount_can_pay:,.0f} today, with the remaining
₦{remaining:,.0f} to be paid by {pay_remaining_by}.

I am {relationship} and {commitment}.
This is a temporary situation and I am committed
to clearing the full balance by {pay_remaining_by}.

I would appreciate your understanding and
confirmation of this arrangement.

Thank you for your consideration.

Yours faithfully,
[Your Name]
[Your Phone Number]"""

                return {"message": message, "type": "negotiation_draft"}

            else:
                return {"error": f"Unknown tool: {name}"}

        except Exception as e:
            return {"error": str(e)}

    def _bill_sort_key(self, bill: dict) -> tuple:
        """
        Sort bills: CRITICAL (due ≤3 days) first, then category priority,
        then days until due.
        """
        today = datetime.utcnow().date()
        due = datetime.strptime(bill["due_date"], "%Y-%m-%d").date()
        days_until_due = (due - today).days
        is_critical = 0 if days_until_due <= 3 else 1
        category = bill.get("category", "other")
        priority = BILL_CATEGORY_PRIORITY.get(category, 99)
        return (is_critical, priority, days_until_due)

    async def _run_prioritisation(
        self, current_balance: float, session_id: str = "default"
    ) -> dict:
        """
        Prioritise bills using ALL available resources (balance + salary).
        Never claims salary covers bills unless mathematically true.
        """
        bills = await self.db.get_bills(session_id=session_id)
        salary = await self.db.get_salary(session_id=session_id)
        today = datetime.utcnow().date()

        priority_map = {
            "rent": 1,
            "loan_savings": 2,
            "loan": 2,
            "utilities": 3,
            "transport": 4,
            "food": 5,
            "healthcare": 6,
            "education": 7,
            "shopping": 8,
            "other": 9,
            "subscriptions": 9,
            "subscription": 9,
        }

        if not bills:
            return {
                "current_balance": current_balance,
                "message": "No bills found. Add your bills first.",
                "salary_status": {"configured": salary is not None},
                "critical_bills": [],
                "upcoming_bills": [],
                "prioritised_bills": [],
                "total_bills": 0,
                "total_bills_due": 0,
                "shortfall": 0,
                "crisis_level": "manageable",
                "crisis_message": "No bills to prioritise.",
                "recommendation_summary": "No bills found — ask user to list their upcoming bills.",
            }

        sorted_bills = sorted(
            bills,
            key=lambda b: (
                priority_map.get(b.get("category", "other"), 9),
                (datetime.strptime(b["due_date"], "%Y-%m-%d").date() - today).days,
            ),
        )

        salary_amount = salary.get("amount", 0) if salary else 0
        pay_date = salary.get("pay_date") if salary else None
        days_to_salary = None
        if pay_date:
            pd = datetime.strptime(pay_date, "%Y-%m-%d").date()
            days_to_salary = (pd - today).days

        total_resources = current_balance + salary_amount
        total_bills = sum(b.get("amount", 0) for b in bills)
        shortfall = max(0, total_bills - total_resources)
        salary_coverage_pct = round(
            (salary_amount / total_bills * 100) if total_bills > 0 else 0, 1
        )

        remaining = total_resources
        results = []

        for bill in sorted_bills:
            amount = bill.get("amount", 0)
            due = datetime.strptime(bill["due_date"], "%Y-%m-%d").date()
            days_until_due = (due - today).days
            can_afford = remaining >= amount
            partial = remaining if (not can_afford and remaining > 0) else None

            if can_afford:
                status = "✅ Full payment possible"
                remaining -= amount
            elif partial and partial > 0:
                status = f"⚠️ Partial — can pay ₦{partial:,.0f} of ₦{amount:,.0f}"
                remaining = 0
            else:
                status = "❌ Cannot pay — negotiate or defer"

            results.append({
                "name": bill["name"],
                "amount": amount,
                "due_date": bill["due_date"],
                "days_until_due": days_until_due,
                "category": bill.get("category", "other"),
                "status": status,
                "can_afford": can_afford,
                "partial_amount": partial,
                "critical": days_until_due <= 7,
                "due_before_payday": pay_date is None or due <= datetime.strptime(pay_date, "%Y-%m-%d").date(),
            })

        if shortfall == 0:
            crisis_level = "manageable"
            crisis_message = "You can cover all bills with your balance + salary."
        elif shortfall < salary_amount * 0.5:
            crisis_level = "tight"
            crisis_message = (
                f"Tight but manageable with careful prioritisation. Gap: ₦{shortfall:,.0f}"
            )
        else:
            crisis_level = "critical"
            crisis_message = (
                f"CRITICAL: Bills exceed all resources by ₦{shortfall:,.0f}. Negotiation required."
            )

        critical_bills = [b for b in results if b["days_until_due"] <= 7]
        upcoming_bills = [b for b in results if b["days_until_due"] > 7]
        negotiation_needed = [b["name"] for b in results if not b["can_afford"]]

        salary_status = {
            "configured": salary is not None,
            "amount": salary_amount,
            "pay_date": pay_date,
            "days_to_salary": days_to_salary,
            "covers_shortfall": shortfall == 0,
            "message": (
                f"Salary ₦{salary_amount:,.0f} covers only {salary_coverage_pct}% of "
                f"₦{total_bills:,.0f} in bills — does NOT cover the rest."
                if salary_amount < total_bills
                else f"Salary ₦{salary_amount:,.0f} covers all bills."
                if salary_amount > 0
                else "Salary not configured."
            ),
        }

        can_cover_all = shortfall == 0
        recommendation_summary = (
            f"Balance ₦{current_balance:,.0f} + salary ₦{salary_amount:,.0f} = "
            f"₦{total_resources:,.0f} vs bills ₦{total_bills:,.0f}. "
            f"{'All bills covered.' if can_cover_all else f'SHORTFALL ₦{shortfall:,.0f} — salary does NOT cover the rest.'} "
            f"{crisis_message}"
        )

        return {
            "current_balance": current_balance,
            "salary_amount": salary_amount,
            "salary_pay_date": pay_date,
            "days_to_salary": days_to_salary,
            "total_resources": total_resources,
            "total_bills": total_bills,
            "total_bills_due": total_bills,
            "shortfall": shortfall,
            "salary_covers_pct": salary_coverage_pct,
            "crisis_level": crisis_level,
            "crisis_message": crisis_message,
            "prioritised_bills": results,
            "critical_bills": critical_bills,
            "upcoming_bills": upcoming_bills,
            "balance_after_all": remaining,
            "negotiation_needed": negotiation_needed,
            "salary_status": salary_status,
            "payday_forecast": {
                "will_make_payday": can_cover_all,
                "bills_due_before_payday": total_bills,
                "balance_after": remaining,
                "verdict": (
                    f"{'YES' if can_cover_all else 'NO'} — "
                    f"{'All bills covered by balance + salary.' if can_cover_all else f'Gap of ₦{shortfall:,.0f} even after salary. Negotiation required.'}"
                ),
            },
            "recommendation_summary": recommendation_summary,
        }

    async def _send_message(self, chat, message):
        """Run synchronous Gemini send_message in a thread pool."""
        return await asyncio.to_thread(chat.send_message, message)

    def _friendly_error(self, error: Exception) -> str:
        msg = str(error)
        if "429" in msg or "quota" in msg.lower():
            return (
                "Gemini API quota is temporarily exceeded — BillGuard switched to "
                "direct MongoDB analysis so you still get an answer."
            )
        if "API key" in msg or "API_KEY" in msg:
            return "Gemini API key is missing or invalid. Check GEMINI_API_KEY in backend/.env"
        return f"Something went wrong: {msg[:200]}"

    def _extract_balance(self, text: str) -> float | None:
        """Extract account balance — NOT bill amounts."""
        patterns = [
            r"(?:current\s+)?(?:account\s+)?balance\s*(?:is|:)?\s*₦?\s*([\d,]+(?:\.\d+)?)",
            r"(?:I\s+)?have\s*₦?\s*([\d,]+(?:\.\d+)?)\s*(?:in\s+my\s+account|left|available|now)",
            r"₦?\s*([\d,]+(?:\.\d+)?)\s*(?:in\s+my\s+account|available|left\s+now)",
            r"(?:only|just)\s*₦?\s*([\d,]+(?:\.\d+)?)\s*(?:left|remaining)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = self._parse_amount(match.group(1))
                if amount > 0:
                    return amount
        return None

    def _extract_balance_from_history(self, history: list) -> float | None:
        """Find balance mentioned in recent conversation."""
        for msg in reversed(history):
            content = msg.get("content", "")
            balance = self._extract_balance(content)
            if balance is not None:
                return balance
        return None

    def _scrub_balance_phrases(self, text: str) -> str:
        """Remove balance phrases so amounts aren't parsed as bills."""
        patterns = [
            r"(?:current\s+)?(?:account\s+)?balance\s*(?:is|:)?\s*₦?\s*[\d,]+(?:\.\d+)?",
            r"(?:I\s+)?have\s*₦?\s*[\d,]+(?:\.\d+)?\s*(?:in\s+my\s+account|left|available|now)",
            r"₦?\s*[\d,]+(?:\.\d+)?\s*(?:in\s+my\s+account|available)",
        ]
        scrubbed = text
        for pattern in patterns:
            scrubbed = re.sub(pattern, " ", scrubbed, flags=re.IGNORECASE)
        return scrubbed

    def _has_bill_keyword(self, text: str) -> bool:
        """Check for bill keywords as whole words (not 'rent' inside 'current')."""
        lower = text.lower()
        for kw in BILL_KEYWORDS:
            if re.search(rf"(?<![a-zA-Z]){re.escape(kw)}(?![a-zA-Z])", lower):
                return True
        return False

    def _parse_due_date(self, text: str) -> str | None:
        """Parse due date fragments into YYYY-MM-DD."""
        months = {
            "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
            "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
            "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
            "nov": 11, "november": 11, "dec": 12, "december": 12,
        }
        iso = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        if iso:
            return iso.group(1)

        # "June 10th" or "due June 10"
        m = re.search(
            r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s+(\d{4}))?",
            text,
            re.IGNORECASE,
        )
        if m:
            month = months.get(m.group(1).lower()[:3], 6)
            day = int(m.group(2))
            year = int(m.group(3)) if m.group(3) else datetime.utcnow().year
            return f"{year}-{month:02d}-{day:02d}"

        # "10 June" or "due 10 June 2026"
        m = re.search(
            r"(?:due\s+)?(?:on\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)(?:\s+(\d{4}))?",
            text,
            re.IGNORECASE,
        )
        if m:
            day = int(m.group(1))
            month = months.get(m.group(2).lower()[:3], 6)
            year = int(m.group(3)) if m.group(3) else datetime.utcnow().year
            return f"{year}-{month:02d}-{day:02d}"
        return None

    def _default_due_date(self, category: str) -> str:
        """Infer a due date when the user didn't provide one."""
        today = datetime.utcnow().date()
        y, m = today.year, today.month

        def bump_month():
            if m == 12:
                return y + 1, 1
            return y, m + 1

        if category == "rent":
            ny, nm = bump_month()
            return f"{ny}-{nm:02d}-01"
        if category == "other":
            last = monthrange(y, m)[1]
            if today.day >= last:
                ny, nm = bump_month()
                last = monthrange(ny, nm)[1]
                return f"{ny}-{nm:02d}-{last}"
            return f"{y}-{m:02d}-{last}"

        day = 15 if category == "loan_savings" else 10
        if today.day >= day:
            ny, nm = bump_month()
            return f"{ny}-{nm:02d}-{day:02d}"
        return f"{y}-{m:02d}-{day:02d}"

    def _default_salary_pay_date(self) -> str:
        """Default salary pay date to the 25th."""
        today = datetime.utcnow().date()
        y, m = today.year, today.month
        if today.day > 25:
            if m == 12:
                return f"{y + 1}-01-25"
            return f"{y}-{m + 1:02d}-25"
        return f"{y}-{m:02d}-25"

    def _parse_amount(self, raw: str) -> float:
        """Parse NGN amounts like '200,000' or '120000,'."""
        cleaned = re.sub(r"[^\d.]", "", raw)
        return float(cleaned) if cleaned else 0.0

    def _guess_category(self, name: str) -> str:
        n = name.lower()
        if any(k in n for k in ["rent", "landlord", "house"]):
            return "rent"
        if any(k in n for k in ["loan", "renmoney", "fairmoney", "piggyvest"]):
            return "loan_savings"
        if any(k in n for k in ["electric", "light", "ekedc", "ikedc", "nepa", "dstv", "netflix", "mtn", "internet", "data"]):
            return "utilities"
        if any(k in n for k in ["debt", "debts"]):
            return "loan_savings"
        if any(k in n for k in ["fuel", "uber", "transport", "car"]):
            return "transport"
        if any(k in n for k in ["food", "grocery"]):
            return "food"
        return "other"

    async def _try_save_from_chat(self, message: str) -> list[dict]:
        """Parse and save bills/salary mentioned inline in chat."""
        saved = []
        balance_amount = self._extract_balance(message)
        scrubbed = self._scrub_balance_phrases(message)
        msg_lower = message.lower()
        seen_bills: set[tuple[str, float]] = set()
        salary_amount: float | None = None

        # ── Salary ──
        if any(k in msg_lower for k in ["earn", "salary", "get paid", "paid on", "paid the"]):
            for pattern in [
                r"salary\s*(?:is|:)?\s*₦?\s*([\d,]+)",
                r"(?:earn(?:ing)?|receive)\s*(?:is|of|a|)?\s*₦?\s*([\d,]+)",
            ]:
                amount_match = re.search(pattern, message, re.IGNORECASE)
                if amount_match:
                    salary_amount = self._parse_amount(amount_match.group(1))
                    break

            if salary_amount and salary_amount > 0:
                pay_date = self._parse_due_date(message) or self._default_salary_pay_date()
                day_match = re.search(
                    r"(?:paid on|pay date|payday|paid)\s*(?:the\s*)?(\d{1,2})(?:st|nd|rd|th)?",
                    message,
                    re.IGNORECASE,
                )
                if day_match:
                    day = int(day_match.group(1))
                    today = datetime.utcnow().date()
                    year, month = today.year, today.month
                    if day < today.day:
                        month += 1
                        if month > 12:
                            month = 1
                            year += 1
                    pay_date = f"{year}-{month:02d}-{day:02d}"

                args = {"amount": salary_amount, "pay_date": pay_date}
                result = await self._execute_tool("save_salary_from_chat", args)
                saved.append({"type": "salary", "args": args, "result": result})

        # ── Bills: keyword + amount (whole-word keywords only) ──
        kw_pattern = "|".join(re.escape(k) for k in BILL_KEYWORDS)
        bill_pattern = re.compile(
            rf"(?<![a-zA-Z])({kw_pattern})(?![a-zA-Z])\s*[-–,]?\s*([\d,]+)",
            re.IGNORECASE,
        )
        for match in bill_pattern.finditer(scrubbed):
            keyword = match.group(1).lower()
            amount = self._parse_amount(match.group(2))
            if amount <= 0 or amount == salary_amount or amount == balance_amount:
                continue

            name, category = BILL_KEYWORDS[keyword]
            key = (name, amount)
            if key in seen_bills:
                continue
            seen_bills.add(key)

            due_date = self._parse_due_date(match.group(0)) or self._default_due_date(category)
            args = {
                "name": name,
                "amount": amount,
                "due_date": due_date,
                "category": category,
            }
            result = await self._execute_tool("save_bill_from_chat", args)
            saved.append({"type": "bill", "args": args, "result": result})

        # ── Fallback: explicit "name is ₦X" clauses ──
        if not any(s["type"] == "bill" for s in saved):
            bill_clauses = re.split(
                r"\band also\b|\balso have\b|\band\b(?=\s+\w+\s+₦)|,",
                scrubbed,
                flags=re.IGNORECASE,
            )
            for clause in bill_clauses:
                if not re.search(r"₦|\d{3,}", clause):
                    continue
                if not self._has_bill_keyword(clause):
                    continue

                amount_match = re.search(r"₦?\s*([\d,]+(?:\.\d+)?)", clause)
                if not amount_match:
                    continue
                amount = self._parse_amount(amount_match.group(1))
                if amount == salary_amount or amount == balance_amount:
                    continue

                name = "Bill"
                clause_lower = clause.lower()
                if re.search(r"(?<![a-zA-Z])rent(?![a-zA-Z])", clause_lower):
                    name = "House Rent"
                elif any(re.search(rf"(?<![a-zA-Z]){k}(?![a-zA-Z])", clause_lower) for k in ("loan", "renmoney", "debt", "debts")):
                    name = "Loan Repayment"
                elif any(k in clause_lower for k in ["electric", "light", "ekedc"]):
                    name = "Electricity"
                elif re.search(r"(?<![a-zA-Z])(data|internet)(?![a-zA-Z])", clause_lower):
                    name = "Data Subscription"
                else:
                    name_match = re.match(r"^[\s,]*(?:my\s+)?(.+?)\s+(?:is|₦|-)", clause, re.IGNORECASE)
                    if name_match:
                        name = name_match.group(1).strip().title()

                key = (name, amount)
                if key in seen_bills:
                    continue
                seen_bills.add(key)

                category = self._guess_category(name + " " + clause)
                due_date = self._parse_due_date(clause) or self._default_due_date(category)
                args = {
                    "name": name,
                    "amount": amount,
                    "due_date": due_date,
                    "category": category,
                }
                result = await self._execute_tool("save_bill_from_chat", args)
                saved.append({"type": "bill", "args": args, "result": result})

        return saved

    async def _yield_saved_tool_events(self, saved_items: list[dict]) -> AsyncIterator[dict]:
        """Emit tool_call / tool_result SSE events for saved items."""
        for item in saved_items:
            tool = "save_salary_from_chat" if item["type"] == "salary" else "save_bill_from_chat"
            args = item.get("args", {})
            yield {
                "type": "tool_call",
                "tool": tool,
                "message": self._tool_thinking_message(tool, args),
            }
            yield {
                "type": "tool_result",
                "tool": tool,
                "result_summary": item["result"].get("message", "Saved"),
            }

    async def _build_full_situation_analysis(
        self,
        balance: float,
        prio: dict,
        total_bills: float,
        salary: dict | None,
        saved_bills: list[dict] | None = None,
    ) -> str:
        """Detailed, honest financial analysis — never false comfort on salary."""
        sal_amt = prio.get("salary_amount") or (salary.get("amount", 0) if salary else 0)
        pay_date = prio.get("salary_pay_date") or (salary.get("pay_date", "unknown") if salary else "unknown")
        shortfall = prio.get("shortfall", max(0, total_bills - balance - sal_amt))
        coverage_pct = prio.get("salary_covers_pct", 0)
        all_bills = prio.get("prioritised_bills", [])
        crisis_level = prio.get("crisis_level", "manageable")

        lines = ["**The honest picture:**\n"]
        if sal_amt > 0:
            lines.append(
                f"Your salary of **₦{sal_amt:,.0f}** covers only **{coverage_pct}%** of your "
                f"**₦{total_bills:,.0f}** in bills."
            )
            if shortfall > 0:
                lines.append(
                    f"Even with your **₦{balance:,.0f}** balance + salary, you're short by "
                    f"**₦{shortfall:,.0f}**. Salary does **NOT** cover the rest."
                )
            else:
                lines.append("Balance + salary together cover all bills. ✅")
        else:
            lines.append(
                f"**Current balance:** ₦{balance:,.0f} | **Bills due:** ₦{total_bills:,.0f}"
            )

        full_pay = [b for b in all_bills if b.get("can_afford")]
        partial_pay = [b for b in all_bills if b.get("partial_amount")]
        cannot_pay = [b for b in all_bills if not b.get("can_afford") and not b.get("partial_amount")]

        if full_pay or partial_pay or cannot_pay:
            lines.append("\nHere's what your resources can realistically do:\n")

        if full_pay:
            total_full = sum(b["amount"] for b in full_pay)
            lines.append(f"**Pay in full (₦{total_full:,.0f} total):**")
            for b in full_pay:
                lines.append(
                    f"✅ **{b['name']}** — ₦{b['amount']:,.0f} (due {b['due_date']}) — pay this first"
                )

        if partial_pay:
            lines.append("\n**Partial payment:**")
            for b in partial_pay:
                partial = b["partial_amount"]
                remaining_amt = b["amount"] - partial
                lines.append(
                    f"⚠️ **{b['name']}** — put ₦{partial:,.0f} toward ₦{b['amount']:,.0f} "
                    f"(₦{remaining_amt:,.0f} remaining — needs negotiation)"
                )

        if cannot_pay:
            lines.append("\n**Cannot pay this month — negotiate:**")
            for b in cannot_pay:
                cat = b.get("category", "other")
                if cat == "rent":
                    tip = "Call landlord — explain situation, offer partial now + rest next month"
                elif cat in ("loan_savings", "loan"):
                    tip = "Call lender (RenMoney etc.) — ask for 1-month extension. Lenders prefer extension over default"
                else:
                    tip = "Defer if possible — explain to creditor"
                lines.append(f"❌ **{b['name']}** ₦{b['amount']:,.0f}")
                lines.append(f"   → {tip}")

        lines.append(f"\n**After paying what you can:**")
        lines.append(
            f"Balance remaining: **₦{max(0, prio.get('balance_after_all', 0)):,.0f}** "
            "(keep for transport and food)"
        )

        if crisis_level == "critical" and shortfall > 0:
            lines.append(f"\n**To close the ₦{shortfall:,.0f} gap, also consider:**")
            lines.append("- Salary advance from your employer (ask HR directly)")
            lines.append("- Carbon (getcarbon.co) or FairMoney for emergency bridge loan")
            lines.append("- Branch or PalmCredit for quick loans")
            lines.append("- Ask a trusted family member to cover rent — repay from next salary")
            if sal_amt > 0 and pay_date != "unknown":
                lines.append(
                    f"\nWhile you negotiate with creditors, these can help before **{pay_date}**."
                )

        lines.append(
            "\n**Want me to draft your message to the landlord or RenMoney? Just say which one.**"
        )
        return "\n".join(lines)

    async def _build_saved_confirmation(
        self,
        saved_items: list[dict],
        balance: float | None = None,
        history: list | None = None,
    ) -> str:
        """Warm confirmation after bills/salary saved — with correct maths and optional plan."""
        bills_saved = [s for s in saved_items if s["type"] == "bill"]
        salaries = [s for s in saved_items if s["type"] == "salary"]

        sid = self._current_session_id
        db_bills = await self.db.get_bills(session_id=sid)
        salary = await self.db.get_salary(session_id=sid)
        total_bills = sum(b.get("amount", 0) for b in db_bills)

        if balance is None and history:
            balance = self._extract_balance_from_history(history)

        lines = []
        if bills_saved:
            lines.append(f"Got it — saved **{len(bills_saved)}** bill{'s' if len(bills_saved) != 1 else ''}:\n")
            for item in bills_saved:
                args = item["args"]
                due = datetime.strptime(args["due_date"], "%Y-%m-%d").strftime("%b %d")
                lines.append(f"- **{args['name']}** — ₦{args['amount']:,.0f} (due {due})")
        elif db_bills:
            lines.append(f"**{len(db_bills)} bills** on file:\n")
            for b in db_bills[:8]:
                lines.append(f"- **{b['name']}** — ₦{b['amount']:,.0f}")

        if salaries:
            sal = salaries[0]["args"]
            lines.append(f"\n**Salary:** ₦{sal['amount']:,.0f} saved (pay date {sal['pay_date']}).")
        elif salary:
            lines.append(f"\n**Salary:** ₦{salary['amount']:,.0f} (pay date {salary['pay_date']}).")

        sal_amt = (salaries[0]["args"]["amount"] if salaries else salary.get("amount", 0) if salary else 0)
        lines.append(f"\n**Total bills due:** ₦{total_bills:,.0f}")

        if sal_amt > 0:
            total_resources = balance + sal_amt if balance is not None else sal_amt
            gap = total_bills - total_resources
            lines.append(f"**Salary:** ₦{sal_amt:,.0f}")
            if balance is not None:
                lines.append(
                    f"**Total resources (balance + salary):** ₦{total_resources:,.0f}"
                )
            lines.append(
                f"**Calculation:** ₦{total_resources:,.0f} − ₦{total_bills:,.0f} = "
                f"{'−' if gap > 0 else ''}₦{abs(gap):,.0f}"
            )
            if gap > 0:
                pct = round(sal_amt / total_bills * 100, 1) if total_bills > 0 else 0
                lines.append(
                    f"\nYour salary covers only **{pct}%** of bills. "
                    f"**Shortfall: ₦{gap:,.0f}** — salary does NOT cover the rest."
                )
            elif total_bills > 0:
                lines.append("\nBalance + salary cover all listed bills. ✅")

        if balance is not None:
            prio = await self._run_prioritisation(balance, session_id=sid)
            lines.append("\n---\n")
            lines.append(
                await self._build_full_situation_analysis(
                    balance, prio, total_bills, salary or (salaries[0]["args"] if salaries else None)
                )
            )
        elif total_bills > 0:
            lines.append(
                "\nWhat's your **current account balance**? "
                "I'll build your priority payment plan immediately."
            )

        return "\n".join(lines)

    async def _stream_text_chunks(self, text: str) -> AsyncIterator[dict]:
        words = text.split(" ")
        chunk = ""
        for i, word in enumerate(words):
            chunk += word + " "
            if len(chunk) > 50 or i == len(words) - 1:
                yield {"type": "text", "content": chunk}
                chunk = ""
                await asyncio.sleep(0.015)

    async def _fallback_management_plan(self, balance: float | None) -> str:
        sid = self._current_session_id
        summary = await self.db.get_financial_summary(session_id=sid)
        if balance is None:
            balance = summary.get("net", 0)

        prio = await self._run_prioritisation(balance, session_id=sid)
        salary = await self.db.get_salary(session_id=sid)
        total_bills = prio.get("total_bills", summary.get("total_bills_due", 0))

        return await self._build_full_situation_analysis(
            balance, prio, total_bills, salary
        )

    async def _fallback_payday_forecast(self, balance: float | None) -> str:
        sid = self._current_session_id
        salary = await self.db.get_salary(session_id=sid)
        if not salary:
            return (
                "I don't have your salary info yet. What's your monthly salary "
                "and when do you get paid? (e.g. 'I earn ₦450,000 paid on the 25th')"
            )

        if balance is None:
            summary = await self.db.get_financial_summary(session_id=sid)
            balance = summary.get("net", 0)

        prio = await self._run_prioritisation(balance, session_id=sid)
        forecast = prio.get("payday_forecast", {})
        sal_amt = salary.get("amount", 0)
        pay_date = salary.get("pay_date", "unknown")
        will_make = forecast.get("will_make_payday", False)
        shortfall = prio.get("shortfall", 0)
        total_bills = prio.get("total_bills", 0)
        total_resources = prio.get("total_resources", balance + sal_amt)

        verdict = "YES — all bills covered" if will_make else "NO — shortfall remains"
        lines = [
            f"**{verdict}**\n",
            f"- Current balance: **₦{balance:,.0f}**",
            f"- Salary: **₦{sal_amt:,.0f}** on **{pay_date}**",
            f"- Total resources: **₦{total_resources:,.0f}** (balance + salary)",
            f"- Total bills: **₦{total_bills:,.0f}**",
        ]

        if shortfall > 0:
            lines.append(
                f"- **Gap: ₦{shortfall:,.0f}** — salary does **NOT** cover all bills. "
                f"Negotiation required."
            )
            lines.append(
                f"- Calculation: ₦{total_resources:,.0f} − ₦{total_bills:,.0f} = "
                f"**−₦{shortfall:,.0f}**"
            )
        else:
            lines.append(f"- Remaining after all bills: **₦{prio.get('balance_after_all', 0):,.0f}**")

        if not will_make:
            lines.append("\n**Bills you cannot fully pay:**")
            for name in prio.get("negotiation_needed", [])[:5]:
                lines.append(f"- {name}")

        lines.append("\n---\n")
        lines.append(
            await self._build_full_situation_analysis(
                balance, prio, total_bills, salary
            )
        )
        return "\n".join(lines)

    async def _fallback_chat(
        self,
        message: str,
        history: list | None = None,
        pre_saved: list[dict] | None = None,
    ) -> AsyncIterator[dict]:
        """Respond using MongoDB tools directly when Gemini is unavailable."""
        yield {"type": "status", "phase": "thinking", "message": "Analysing via MongoDB…"}
        msg = message.lower()
        history = history or []
        history_text = " ".join(m.get("content", "") for m in history).lower()
        balance = self._extract_balance(message)

        # 1. Save bills/salary from chat first (skip if already saved in chat())
        saved_items = pre_saved if pre_saved is not None else await self._try_save_from_chat(message)
        if saved_items:
            if pre_saved is None:
                async for event in self._yield_saved_tool_events(saved_items):
                    yield event

            if balance is None:
                balance = self._extract_balance_from_history(history)

            if balance is not None:
                yield {
                    "type": "tool_call",
                    "tool": "prioritise_bills",
                    "message": self._tool_thinking_message("prioritise_bills", {"current_balance": balance}),
                }
                prio = await self._run_prioritisation(balance, session_id=self._current_session_id)
                yield {
                    "type": "tool_result",
                    "tool": "prioritise_bills",
                    "result_summary": self._summarise_result("prioritise_bills", prio),
                }

            text = await self._build_saved_confirmation(saved_items, balance=balance, history=history)

        elif any(k in msg for k in ["manage", "how do i", "what should i", "action plan", "help me"]):
            yield {"type": "tool_call", "tool": "get_financial_summary", "message": "📊 Checking your finances…"}
            await self.db.get_financial_summary(session_id=self._current_session_id)
            yield {"type": "tool_result", "tool": "get_financial_summary", "result_summary": "Summary loaded"}
            yield {"type": "tool_call", "tool": "get_bills", "message": "📋 Loading bills…"}
            bills = await self.db.get_bills(session_id=self._current_session_id)
            yield {"type": "tool_result", "tool": "get_bills", "result_summary": f"Found {len(bills)} bills"}
            text = await self._fallback_management_plan(balance)

        elif any(k in msg for k in ["payday", "make it", "will i make", "cover", "afford until"]):
            yield {"type": "tool_call", "tool": "get_salary_info", "message": "💰 Checking salary…"}
            salary = await self.db.get_salary(session_id=self._current_session_id)
            summary = "Salary loaded" if salary else "No salary on file"
            yield {"type": "tool_result", "tool": "get_salary_info", "result_summary": summary}
            yield {"type": "tool_call", "tool": "get_bills", "message": "📋 Loading bills before payday…"}
            bills = await self.db.get_bills(session_id=self._current_session_id)
            yield {"type": "tool_result", "tool": "get_bills", "result_summary": f"Found {len(bills)} bills"}
            if balance is not None:
                yield {"type": "tool_call", "tool": "prioritise_bills", "message": f"⚡ Forecasting with ₦{balance:,.0f}…"}
                prio = await self._run_prioritisation(balance, session_id=self._current_session_id)
                yield {"type": "tool_result", "tool": "prioritise_bills", "result_summary": prio.get("payday_forecast", {}).get("verdict", "Done")}
            text = await self._fallback_payday_forecast(balance)

        elif any(k in msg for k in ["subscription", "cut", "cancel", "hidden", "recurring"]):
            yield {"type": "tool_call", "tool": "get_transactions", "message": "🔍 Scanning recurring charges…"}
            result = await self._execute_tool("get_transactions", {"category": "utilities", "limit": 50})
            yield {"type": "tool_result", "tool": "get_transactions", "result_summary": f"Found {result.get('count', 0)} transactions"}
            subs = [t for t in result.get("transactions", []) if t.get("type") == "debit"]
            total = sum(t["amount"] for t in subs)
            lines = ["**Subscriptions & recurring charges:**\n"]
            for t in subs[:10]:
                lines.append(f"- {t['description'][:45]} — **₦{t['amount']:,.0f}**")
            lines.append(f"\n**Total monthly (detected):** ₦{total:,.0f}")
            lines.append("\n**Cancel first (lowest value):** Showmax → Spotify → Canva → ChatGPT")
            lines.append(f"**Potential saving:** ~₦{min(total * 0.4, 20000):,.0f}/month")
            text = "\n".join(lines)

        elif any(k in msg for k in ["pay first", "priorit", "what do i pay"]):
            bal = balance if balance is not None else 87000
            yield {"type": "tool_call", "tool": "prioritise_bills", "message": f"⚡ Prioritising with ₦{bal:,.0f}…"}
            result = await self._run_prioritisation(bal, session_id=self._current_session_id)
            yield {"type": "tool_result", "tool": "prioritise_bills", "result_summary": result.get("recommendation_summary", "Done")}
            lines = [f"**Payment plan for ₦{bal:,.0f}:**\n"]
            for i, b in enumerate(result.get("prioritised_bills", [])[:8], 1):
                lines.append(f"{i}. {b['status']} **{b['name']}** — ₦{b['amount']:,.0f}")
            text = "\n".join(lines)

        elif any(k in msg for k in ["where", "going", "breakdown", "spending"]) and "breakdown" not in history_text and "where your money" not in history_text:
            yield {"type": "tool_call", "tool": "get_financial_summary", "message": "📊 Pulling spending breakdown…"}
            summary = await self.db.get_financial_summary(session_id=self._current_session_id)
            yield {"type": "tool_result", "tool": "get_financial_summary", "result_summary": f"Spending: ₦{summary['total_outflow']:,.0f}"}
            lines = ["**Where your money went (last 30 days):**\n"]
            for cat in summary.get("spending_by_category", []):
                name = (cat["category"] or "other").replace("_", " ").title()
                lines.append(f"- **{name}:** ₦{cat['total']:,.0f}")
            lines.append(f"\n**Net:** ₦{summary['net']:,.0f} | **Bills due:** ₦{summary['total_bills_due']:,.0f}")
            text = "\n".join(lines)

        elif any(k in msg for k in ["critical", "urgent", "this week"]):
            yield {"type": "tool_call", "tool": "get_bills", "message": "📋 Loading critical bills…"}
            prio = await self._run_prioritisation(balance or 0, session_id=self._current_session_id)
            yield {"type": "tool_result", "tool": "get_bills", "result_summary": f"{len(prio.get('critical_bills', []))} critical"}
            lines = ["**Critical bills (≤7 days):**\n"]
            for b in prio.get("critical_bills", []):
                flag = "🔴" if b["days_until_due"] <= 3 else "🟡"
                lines.append(f"- {flag} **{b['name']}** ₦{b['amount']:,.0f} — {b['days_until_due']} days")
            text = "\n".join(lines) if prio.get("critical_bills") else "No critical bills in the next 7 days."

        else:
            # Default: don't repeat breakdown if already shown — give actionable next step
            if "breakdown" in history_text or "where your money" in history_text:
                text = await self._fallback_management_plan(balance)
            else:
                yield {"type": "tool_call", "tool": "get_financial_summary", "message": "📊 Checking your data…"}
                summary = await self.db.get_financial_summary(session_id=self._current_session_id)
                yield {"type": "tool_result", "tool": "get_financial_summary", "result_summary": "Data loaded"}
                text = (
                    f"You have **₦{summary['net']:,.0f}** net over 30 days and "
                    f"**₦{summary['total_bills_due']:,.0f}** in bills due.\n\n"
                    "Tell me your current balance and I'll build a payment plan, "
                    "or ask **'will I make it to payday?'**"
                )

        yield {"type": "status", "phase": "writing", "message": "Writing your answer…"}
        async for chunk in self._stream_text_chunks(text):
            yield chunk

    async def chat(self, message: str, session_id: str = "default") -> AsyncIterator[dict]:
        """
        Main chat method. Streams reasoning steps and final response.
        Yields dicts: {type: "status"|"tool_call"|"tool_result"|"text"|"done"|"error"}
        """
        self._current_session_id = session_id
        yield {"type": "status", "phase": "connecting", "message": "Connecting to BillGuard…"}

        history = await self.db.get_session_history(session_id, limit=6)
        gemini_history = [{"role": m["role"], "parts": [m["content"]]} for m in history]

        await self.db.save_session_message(session_id, "user", message)
        yield {"type": "status", "phase": "thinking", "message": "Reading your question…"}

        full_response_text = ""
        balance = self._extract_balance(message) or self._extract_balance_from_history(history)
        saved_items = await self._try_save_from_chat(message)
        if saved_items:
            async for event in self._yield_saved_tool_events(saved_items):
                yield event

            if balance is not None:
                yield {
                    "type": "tool_call",
                    "tool": "prioritise_bills",
                    "message": self._tool_thinking_message("prioritise_bills", {"current_balance": balance}),
                }
                prio = await self._run_prioritisation(balance, session_id=session_id)
                yield {
                    "type": "tool_result",
                    "tool": "prioritise_bills",
                    "result_summary": self._summarise_result("prioritise_bills", prio),
                }

        try:
            yield {"type": "status", "phase": "thinking", "message": "Consulting Gemini 2.0 Flash…"}
            chat = self.model.start_chat(history=gemini_history)
            response = await self._send_message(chat, message)

            max_iterations = 12
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                if not response.candidates or not response.candidates[0].content.parts:
                    raise ValueError("Empty response from Gemini")

                part = response.candidates[0].content.parts[0]

                if hasattr(part, "function_call") and part.function_call:
                    fn = part.function_call
                    tool_name = fn.name
                    tool_args = dict(fn.args) if fn.args else {}

                    yield {
                        "type": "tool_call",
                        "tool": tool_name,
                        "message": self._tool_thinking_message(tool_name, tool_args),
                    }

                    tool_result = await self._execute_tool(tool_name, tool_args)

                    yield {
                        "type": "tool_result",
                        "tool": tool_name,
                        "result_summary": self._summarise_result(tool_name, tool_result),
                    }

                    response = await self._send_message(
                        chat,
                        genai.protos.Content(
                            parts=[genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=tool_name,
                                    response={"result": json.dumps(tool_result, default=str)},
                                )
                            )]
                        ),
                    )
                else:
                    text = part.text if hasattr(part, "text") else ""
                    full_response_text = text
                    yield {"type": "status", "phase": "writing", "message": "Composing your answer…"}
                    async for chunk in self._stream_text_chunks(text):
                        yield chunk
                    break

        except Exception as e:
            friendly = self._friendly_error(e)
            if "429" in str(e) or "quota" in str(e).lower():
                async for event in self._fallback_chat(message, history, pre_saved=saved_items):
                    if event["type"] == "text":
                        full_response_text += event.get("content", "")
                    yield event
            else:
                yield {"type": "error", "content": friendly}
                full_response_text = friendly

        if not full_response_text and saved_items:
            full_response_text = await self._build_saved_confirmation(
                saved_items, balance=balance, history=history
            )
            yield {"type": "status", "phase": "writing", "message": "Writing your answer…"}
            async for chunk in self._stream_text_chunks(full_response_text):
                yield chunk

        if full_response_text:
            await self.db.save_session_message(session_id, "model", full_response_text)

        yield {"type": "status", "phase": "finishing", "message": "Done ✓"}
        yield {"type": "done"}

    def _tool_thinking_message(self, tool_name: str, args: dict) -> str:
        messages = {
            "get_financial_summary": "📊 Pulling your complete financial picture from MongoDB...",
            "get_transactions": f"🔍 Checking your {args.get('category', 'all')} transactions...",
            "get_bills": "📋 Loading your upcoming bills...",
            "get_salary_info": "💰 Checking your salary and pay date...",
            "prioritise_bills": f"⚡ Running bill prioritisation with balance of ₦{args.get('current_balance', 0):,.0f}...",
            "save_bill_from_chat": f"💾 Saving {args.get('name', 'bill')} to MongoDB...",
            "save_salary_from_chat": "💾 Saving salary info to MongoDB...",
            "get_spending_insights": "🔍 Analysing recurring charges from your statement...",
            "mark_bill_paid_from_chat": (
                f"✓ Marking {args.get('bill_name', 'bill')} as paid in MongoDB..."
            ),
            "draft_negotiation_message": "✍️ Drafting your negotiation message...",
        }
        return messages.get(tool_name, f"🔧 Running {tool_name}...")

    def _summarise_result(self, tool_name: str, result: dict) -> str:
        if "error" in result:
            return f"Error: {result['error']}"

        if tool_name == "get_financial_summary":
            inflow = result.get("total_inflow", 0)
            outflow = result.get("total_outflow", 0)
            bills = result.get("total_bills_due", 0)
            return f"Income: ₦{inflow:,.0f} | Spending: ₦{outflow:,.0f} | Bills due: ₦{bills:,.0f}"

        if tool_name == "get_transactions":
            return f"Found {result.get('count', 0)} transactions"

        if tool_name == "get_bills":
            count = result.get("total_bills", 0)
            return f"Found {count} upcoming bills"

        if tool_name == "get_salary_info":
            if "pay_date" in result:
                return f"Salary: ₦{result.get('amount', 0):,.0f} on {result.get('pay_date')}"
            return "No salary info found"

        if tool_name == "prioritise_bills":
            return result.get("recommendation_summary", "Prioritisation complete")

        if tool_name == "save_bill_from_chat":
            return result.get("message", "Bill saved")

        if tool_name == "save_salary_from_chat":
            return result.get("message", "Salary saved")

        if tool_name == "get_spending_insights":
            return result.get("insight", result.get("error", "Done"))

        if tool_name == "mark_bill_paid_from_chat":
            return result.get("message", "Bill marked as paid")

        if tool_name == "draft_negotiation_message":
            return "Negotiation message drafted"

        return "Done"
