"""
Clean and summarize transactions CSV.
- normalize status and currency
- parse dates into ISO format
- clean amount to float (remove $)
- fill missing txn_id by generating a unique id
- detect duplicates by (date, merchant, amount, account_id)
- output: cleaned CSV and summary JSON
"""
from __future__ import annotations
import csv
import re
from datetime import datetime
from pathlib import Path
import json
import uuid
from typing import List, Dict, Tuple

INPUT = Path(__file__).parent / "transactions.csv"
CLEANED = Path(__file__).parent / "transactions_cleaned.csv"
SUMMARY = Path(__file__).parent / "transactions_summary.json"

STATUS_MAP = {
    "success": "SUCCESS",
    "failed": "FAILED",
    "pending": "PENDING",
    "failed": "FAILED",
}

CURRENCY_MAP = {"inr": "INR", "usd": "USD", "$": "USD"}

DATE_FORMATS = [
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%d-%m-%Y",
    "%d-%m-%Y",
    "%d-%m-%Y",
    "%Y-%m-%d",
    "%Y/%m/%d",
]


def parse_date(s: str) -> str:
    s = s.strip()
    if not s:
        return ""
    # try common formats
    for fmt in ["%d-%m-%Y", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d/%m/%Y"]:
        try:
            d = datetime.strptime(s, fmt)
            return d.date().isoformat()
        except Exception:
            pass
    # fallback: attempt to parse with day and month swapped if has '/'
    try:
        d = datetime.fromisoformat(s)
        return d.date().isoformat()
    except Exception:
        pass
    # last resort: extract numbers
    m = re.search(r"(\d{2})[^\d]?(\d{2})[^\d]?(\d{4})", s)
    if m:
        dd, mm, yyyy = m.groups()
        try:
            d = datetime(int(yyyy), int(mm), int(dd))
            return d.date().isoformat()
        except Exception:
            pass
    return s


def normalize_status(s: str) -> str:
    if not s:
        return ""
    key = s.strip().lower()
    return STATUS_MAP.get(key, s.strip().upper())


def normalize_currency(s: str) -> str:
    if not s:
        return ""
    key = s.strip().lower()
    if key in CURRENCY_MAP:
        return CURRENCY_MAP[key]
    return s.strip().upper()


def parse_amount(s: str) -> float:
    if not s:
        return 0.0
    s = s.replace(',', '').strip()
    s = s.replace('$', '')
    try:
        return float(s)
    except Exception:
        # try to extract number
        m = re.search(r"([-+]?[0-9]*\.?[0-9]+)", s)
        if m:
            return float(m.group(1))
    return 0.0


def generate_txn_id() -> str:
    return "GEN-" + uuid.uuid4().hex[:12].upper()


def read_transactions(path: Path) -> List[Dict[str, str]]:
    with path.open(newline='') as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def write_cleaned(path: Path, rows: List[Dict[str, str]]):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def process(infile: Path) -> Tuple[List[Dict[str, str]], Dict]:
    rows = read_transactions(infile)
    seen_keys = set()
    cleaned = []
    duplicates = []
    counts = {"total": 0, "by_status": {}, "by_currency": {}, "by_account": {}}

    for r in rows:
        counts['total'] += 1
        # fill txn id
        txn = r.get('txn_id', '')
        if not txn or not txn.strip():
            txn = generate_txn_id()
        # normalize
        date = parse_date(r.get('date', ''))
        merchant = (r.get('merchant') or '').strip()
        amount = parse_amount(r.get('amount', ''))
        currency = normalize_currency(r.get('currency', ''))
        status = normalize_status(r.get('status', ''))
        category = (r.get('category') or '').strip()
        account_id = (r.get('account_id') or '').strip()
        notes = (r.get('notes') or '').strip()

        # update counts
        counts['by_status'][status] = counts['by_status'].get(status, 0) + 1
        counts['by_currency'][currency] = counts['by_currency'].get(currency, 0) + 1
        counts['by_account'][account_id] = counts['by_account'].get(account_id, 0) + 1

        key = (date, merchant.lower(), round(amount, 2), account_id)
        record = {
            'txn_id': txn,
            'date': date,
            'merchant': merchant,
            'amount': f"{amount:.2f}",
            'currency': currency,
            'status': status,
            'category': category,
            'account_id': account_id,
            'notes': notes,
        }
        if key in seen_keys:
            record['duplicate'] = 'TRUE'
            duplicates.append(record)
        else:
            record['duplicate'] = 'FALSE'
            seen_keys.add(key)
            cleaned.append(record)

    summary = {
        'counts': counts,
        'duplicates': len(duplicates),
        'duplicate_samples': duplicates[:5],
    }
    return cleaned, summary


if __name__ == '__main__':
    cleaned, summary = process(INPUT)
    write_cleaned(CLEANED, cleaned)
    with SUMMARY.open('w') as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote {len(cleaned)} cleaned rows to {CLEANED}")
    print(f"Summary written to {SUMMARY}")
