import csv
from pathlib import Path
from datetime import datetime
import re
from statistics import median
from typing import Tuple, List, Dict
from . import llm

LLM_BATCH_SIZE = 10


def parse_date(s: str) -> str:
    s = (s or '').strip()
    if not s:
        return ''
    for fmt in ("%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    # last resort
    m = re.search(r"(\d{2})[^\d]?(\d{2})[^\d]?(\d{4})", s)
    if m:
        d, mth, y = m.groups()
        try:
            return datetime(int(y), int(mth), int(d)).date().isoformat()
        except Exception:
            pass
    return s


def parse_amount(s: str) -> float:
    if not s:
        return 0.0
    s = s.replace(',', '').replace('$', '').strip()
    try:
        return float(s)
    except Exception:
        m = re.search(r"([-+]?[0-9]*\.?[0-9]+)", s)
        if m:
            return float(m.group(1))
    return 0.0


def normalize_status(s: str) -> str:
    return (s or '').strip().upper()


def normalize_currency(s: str) -> str:
    return (s or '').strip().upper()


def call_llm_batch(records: List[Dict]) -> List[str]:
    # stub: simple heuristic mapping based on merchant/notes
    categories = []
    for r in records:
        m = r.get('merchant','').lower()
        if 'swiggy' in m or 'zomato' in m:
            categories.append('Food')
        elif 'amazon' in m or 'flipkart' in m:
            categories.append('Shopping')
        elif 'irctc' in m or 'makemytrip' in m or 'train' in m:
            categories.append('Travel')
        elif 'ola' in m or 'uber' in m:
            categories.append('Transport')
        elif 'jio' in m or 'recharge' in m:
            categories.append('Utilities')
        elif 'hdfc' in m or 'atm' in m:
            categories.append('Cash Withdrawal')
        elif 'bookmyshow' in m:
            categories.append('Entertainment')
        else:
            categories.append('Other')
    return categories


def detect_anomalies(rows: List[Dict]) -> List[Dict]:
    # per-account median
    acct_amounts = {}
    for r in rows:
        acct = r['account_id']
        acct_amounts.setdefault(acct, []).append(r['amount'])
    acct_median = {a: (median(vals) if vals else 0) for a, vals in acct_amounts.items()}
    anomalies = []
    domestic_merchants = {'swiggy','ola','irctc'}
    for r in rows:
        a = r['amount']
        acct = r['account_id']
        if acct_median.get(acct,0) and a > 3 * acct_median[acct]:
            r.setdefault('flags', []).append('OUTLIER')
            anomalies.append(r)
        if r['currency']=='USD' and r['merchant'].lower() in domestic_merchants:
            r.setdefault('flags', []).append('USD_DOMESTIC')
            anomalies.append(r)
    return anomalies


def process_file(path: str) -> Tuple[Dict, int]:
    path = Path(path)
    rows = []
    with path.open() as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    # cleaning
    cleaned = []
    seen = set()
    for r in rows:
        txn = r.get('txn_id') or ''
        date = parse_date(r.get('date',''))
        merchant = (r.get('merchant') or '').strip()
        amount = parse_amount(r.get('amount',''))
        currency = normalize_currency(r.get('currency',''))
        status = normalize_status(r.get('status',''))
        category = (r.get('category') or '').strip() or 'Uncategorised'
        account_id = (r.get('account_id') or '').strip()
        notes = (r.get('notes') or '').strip()
        key = (date, merchant.lower(), round(amount,2), account_id)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append({
            'txn_id': txn,
            'date': date,
            'merchant': merchant,
            'amount': amount,
            'currency': currency,
            'status': status,
            'category': category,
            'account_id': account_id,
            'notes': notes,
        })

    # anomaly detection
    anomalies = detect_anomalies(cleaned)

    # LLM classify uncategorised (via adapter)
    to_classify = [r for r in cleaned if (not r.get('category') or r.get('category')=='Uncategorised')]
    for i in range(0, len(to_classify), LLM_BATCH_SIZE):
        batch = to_classify[i:i+LLM_BATCH_SIZE]
        cats = llm.classify_batch(batch)
        for rec, c in zip(batch, cats):
            rec['category'] = c

    # narrative summary (one LLM call stub)
    total_by_currency = {}
    merchant_totals = {}
    for r in cleaned:
        total_by_currency[r['currency']] = total_by_currency.get(r['currency'], 0) + r['amount']
        merchant_totals[r['merchant']] = merchant_totals.get(r['merchant'], 0) + r['amount']
    top_merchants = sorted(merchant_totals.items(), key=lambda x: -x[1])[:3]

    narrative_input = {
        'total_by_currency': {k: round(v,2) for k,v in total_by_currency.items()},
        'top_3_merchants': [m for m,_ in top_merchants],
        'anomaly_count': len(anomalies),
    }
    narrative = llm.generate_narrative(narrative_input)

    results = {
        'cleaned_transactions': cleaned,
        'anomalies': anomalies,
        'category_breakdown': {},
        'narrative': narrative,
    }
    # category breakdown
    cb = {}
    for r in cleaned:
        cb[r['category']] = cb.get(r['category'], 0) + r['amount']
    results['category_breakdown'] = {k: round(v,2) for k,v in cb.items()}

    return results, len(cleaned)
