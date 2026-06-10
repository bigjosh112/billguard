"""
Nigerian Bank Statement Parser
Normalises CSV exports from GTBank, Access Bank, Zenith, UBA, and other
Nigerian banks into a unified transaction schema using smart column detection.
"""

import csv
import io
import re
import hashlib
from datetime import datetime
from typing import Optional

# Unicode naira (U+20A6) and common mojibake / alternate encodings
NAIRA_VARIANTS = ("₦", "\u20a6", "&#8358;", "N")


CATEGORY_RULES = [
    (["rent", "landlord", "property", "estate", "housing"], "rent"),
    (["fuel", "petrol", "diesel", "uber", "bolt", "taxify", "keke", "okada",
      "transport", "dangote", "car wash", "mechanic", "tyre", "vehicle",
      "insurance auto", "car insurance"], "transport"),
    (["restaurant", "eatery", "food", "grocery", "shoprite", "justrite",
      "chicken republic", "domino", "pizza", "coldstone", "tantalizer",
      "mr biggs", "supermarket", "market"], "food"),
    (["nepa", "phcn", "electricity", "ekedc", "ikedc", "phedc", "kedco",
      "water", "internet", "mtn", "airtel", "glo", "9mobile", "dstv",
      "gotv", "startimes", "showmax", "netflix", "spotify",
      "amazon prime", "canva", "chatgpt", "openai"], "utilities"),
    (["loan", "repayment", "lendigo", "renmoney", "fairmoney", "carbon",
      "branch", "palmcredit", "okash", "opay loan", "kuda loan",
      "savings", "investment", "piggyvest", "cowrywise", "stash"], "loan_savings"),
    (["salary", "payroll", "wage", "income", "payment from", "credit alert",
      "commission", "freelance", "contract"], "income"),
    (["transfer to", "transfer from", "trf", "nip", "instant payment",
      "send money", "ussd"], "transfer"),
    (["atm", "cash withdrawal", "pos", "cash", "withdra"], "cash"),
    (["hospital", "pharmacy", "clinic", "medical", "health", "chemist",
      "lab", "diagnostic"], "healthcare"),
    (["school", "tuition", "university", "college", "course", "masterclass",
      "udemy", "coursera"], "education"),
    (["jumia", "konga", "paystack", "flutterwave", "shopping", "store",
      "fashion", "clothing", "shoe"], "shopping"),
]

DATE_KEYWORDS_ORDERED = [
    "trans. date", "trans date", "transaction date",
    "posting date", "txn date", "tran date", "booking date",
    "value date", "date",
]

BANK_LABELS = {
    "gtbank": "GTBank",
    "access": "Access Bank",
    "access_new": "Access Bank",
    "zenith": "Zenith Bank",
    "uba": "UBA",
    "smart": "Nigerian Bank",
}


def find_column(headers: list, keywords: list) -> Optional[str]:
    """
    Find the best matching column from a list of keywords.
    headers is the list of actual CSV column names (original case).
    keywords is what we're looking for.
    Returns the actual column name or None.
    """
    headers_lower = [h.lower().strip() for h in headers]
    for keyword in keywords:
        kw = keyword.lower()
        for i, h in enumerate(headers_lower):
            if kw in h or h == kw:
                return headers[i]
    return None


def find_date_column(headers: list) -> Optional[str]:
    """Prefer transaction date columns over value date."""
    for keyword in DATE_KEYWORDS_ORDERED:
        col = find_column(headers, [keyword])
        if col:
            return col
    return None


def categorise(description: str) -> str:
    """Assign a category based on transaction description."""
    desc_lower = description.lower()
    for keywords, category in CATEGORY_RULES:
        if any(kw in desc_lower for kw in keywords):
            return category
    return "other"


def clean_amount(value: str) -> float:
    """Parse Nigerian currency strings, stripping all symbol variants."""
    if not value or str(value).strip() == "":
        return 0.0

    cleaned = str(value)
    for symbol in NAIRA_VARIANTS:
        cleaned = cleaned.replace(symbol, "")
    cleaned = cleaned.replace(",", "").replace(" ", "").strip()
    cleaned = re.sub(r"[^\d.\-]", "", cleaned)

    if not cleaned or cleaned == "-":
        return 0.0
    try:
        return abs(float(cleaned))
    except ValueError:
        return 0.0


def parse_amount(value: str) -> float:
    """Alias for clean_amount (backwards compatibility)."""
    return clean_amount(value)


def parse_date(value: str) -> Optional[str]:
    """Parse various Nigerian bank date formats to YYYY-MM-DD."""
    if not value:
        return None

    value = str(value).strip()
    # Strip time component if present: "03 May 2026 08:55:37"
    value = re.split(r"\s+\d{1,2}:\d{2}", value)[0].strip()
    # ISO format with T
    value = value.split("T")[0].strip()

    formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
        "%d/%m/%y", "%d-%m-%y",
        "%d %b %Y", "%d-%b-%Y", "%d %B %Y",
        "%B %d, %Y", "%b %d, %Y",
        "%Y/%m/%d", "%m/%d/%Y",
        "%d.%m.%Y", "%d.%m.%y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def make_reference(date: str, description: str, amount: float) -> str:
    """Create a dedup reference hash for a transaction."""
    key = f"{date}|{description}|{amount}"
    return hashlib.md5(key.encode()).hexdigest()


class BankStatementParser:
    """
    Auto-detects bank format and normalises to:
    {
        date, description, amount, type (debit/credit),
        balance, category, bank, currency, reference
    }
    """

    def parse(self, csv_text: str) -> list:
        """
        Smart parser that handles Nigerian bank CSV files which
        often have metadata rows before the actual data table.
        """
        delimiter = self._detect_delimiter(csv_text)
        lines = csv_text.splitlines()

        header_keywords = [
            "date", "description", "narration", "debit", "credit",
            "balance", "amount", "withdrawal", "deposit", "details",
            "remarks", "particulars", "reference", "trans",
        ]

        best_header_row = 0
        best_score = 0

        for i, line in enumerate(lines[:20]):
            line_lower = line.lower()
            score = sum(1 for kw in header_keywords if kw in line_lower)
            if score > best_score:
                best_score = score
                best_header_row = i

        if best_score == 0:
            print("ERROR: Could not find header row in first 20 lines")
            print(f"First line was: {lines[0][:100] if lines else 'empty'}")
            return []

        print(f"Found header row at line {best_header_row}: {lines[best_header_row][:100]}")

        csv_from_header = "\n".join(lines[best_header_row:])
        reader = csv.DictReader(io.StringIO(csv_from_header), delimiter=delimiter)
        rows = list(reader)

        if not rows:
            print("ERROR: No data rows found after header")
            return []

        original_headers = list(rows[0].keys())
        print(f"Columns found: {original_headers}")

        cleaned_headers = {}
        for h in original_headers:
            clean = h.strip().lstrip("\ufeff").lstrip("\xef\xbb\xbf")
            cleaned_headers[h] = clean

        clean_rows = []
        for row in rows:
            clean_row = {cleaned_headers.get(k, k): v for k, v in row.items()}
            clean_rows.append(clean_row)

        clean_original_headers = list(cleaned_headers.values())
        headers_lower = [h.lower().strip() for h in clean_original_headers]
        bank = self._detect_bank(headers_lower, clean_original_headers)

        print(f"Detected bank format: {bank}")

        return self._parse_smart(clean_rows, clean_original_headers, bank)

    def _detect_delimiter(self, csv_text: str) -> str:
        """Detect whether the file uses comma, semicolon, or tab."""
        first_lines = "\n".join(csv_text.splitlines()[:5])
        comma_count = first_lines.count(",")
        semicolon_count = first_lines.count(";")
        tab_count = first_lines.count("\t")

        if tab_count > comma_count and tab_count > semicolon_count:
            return "\t"
        if semicolon_count > comma_count:
            return ";"
        return ","

    def _detect_bank(self, headers_lower: list, original_headers: list) -> str:
        header_str = " ".join(headers_lower)

        if "transaction reference" in header_str:
            if "trans. date" in header_str or "trans date" in header_str:
                return "access_new"
        if "value date" in header_str and "debit" in header_str:
            return "gtbank"
        if "withdrawal" in header_str:
            return "access"
        if "remarks" in header_str:
            return "zenith"
        if "posting date" in header_str:
            return "uba"
        return "smart"

    def _parse_smart(self, rows: list, original_headers: list, bank: str = "smart") -> list:
        """
        Universal parser using smart column detection.
        Works for any Nigerian bank CSV format.
        """
        date_col = find_date_column(original_headers)
        desc_col = find_column(original_headers, [
            "description", "narration", "narrative", "details",
            "remarks", "remark", "particulars", "memo",
            "transaction description", "payment details", "ref",
        ])
        debit_col = find_column(original_headers, [
            "debit(₦)", "debit(n)", "debit(ngn)", "debit",
            "withdrawal", "dr", "amount dr", "debit amount",
            "withdrawals", "paid out", "money out",
        ])
        credit_col = find_column(original_headers, [
            "credit(₦)", "credit(n)", "credit(ngn)", "credit",
            "deposit", "cr", "amount cr", "credit amount",
            "deposits", "paid in", "money in",
        ])
        balance_col = find_column(original_headers, [
            "balance after(₦)", "balance after(n)", "balance after(ngn)",
            "balance after", "closing balance", "running balance",
            "ledger balance", "available balance", "balance", "bal",
        ])
        amount_col = find_column(original_headers, [
            "amount", "transaction amount", "txn amount",
        ])

        print(
            f"Parser found columns: date={date_col}, desc={desc_col}, "
            f"debit={debit_col}, credit={credit_col}, balance={balance_col}"
        )

        if not date_col:
            print(f"ERROR: No date column found. Available headers: {original_headers}")
            return []

        bank_label = BANK_LABELS.get(bank, "Nigerian Bank")
        txns = []

        for row in rows:
            date = parse_date(row.get(date_col, ""))
            if not date:
                continue

            desc = str(row.get(desc_col, "") or "").strip()
            debit = clean_amount(row.get(debit_col, "0") if debit_col else "0")
            credit = clean_amount(row.get(credit_col, "0") if credit_col else "0")
            balance = clean_amount(row.get(balance_col, "0") if balance_col else "0")

            if debit > 0:
                amount, txn_type = debit, "debit"
            elif credit > 0:
                amount, txn_type = credit, "credit"
            elif amount_col:
                raw = clean_amount(row.get(amount_col, "0"))
                if raw <= 0:
                    continue
                # Signed amount column: negative = debit
                raw_str = str(row.get(amount_col, "")).strip()
                if raw_str.startswith("-") or raw_str.startswith("("):
                    amount, txn_type = raw, "debit"
                else:
                    amount, txn_type = raw, "credit"
            else:
                continue

            txns.append(self._build(date, desc, amount, txn_type, balance, bank_label))

        return txns

    def _build(self, date, description, amount, txn_type, balance, bank) -> dict:
        return {
            "date": date,
            "description": description.strip(),
            "amount": round(amount, 2),
            "type": txn_type,
            "balance": round(balance, 2),
            "category": categorise(description),
            "bank": bank,
            "currency": "NGN",
            "reference": make_reference(date, description, amount),
        }
