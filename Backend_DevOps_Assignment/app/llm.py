"""
LLM adapter: supports Gemini (Google Generative API) when enabled via env vars.

Environment variables:
  USE_GEMINI=1 or true to enable real calls
  GOOGLE_API_KEY or GEMINI_API_KEY - API key for generative API
  GEMINI_MODEL - model name (default: models/text-bison-001)

If USE_GEMINI is not set, this module falls back to the internal heuristic stub.
"""
import os
from typing import List, Dict

USE_GEMINI = os.getenv('USE_GEMINI', '').lower() in ('1', 'true', 'yes')
API_KEY = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
MODEL = os.getenv('GEMINI_MODEL', 'models/text-bison-001')


def _heuristic_classify(records: List[Dict]) -> List[str]:
    # same heuristics previously used in processor
    cats = []
    for r in records:
        m = r.get('merchant','').lower()
        if 'swiggy' in m or 'zomato' in m:
            cats.append('Food')
        elif 'amazon' in m or 'flipkart' in m:
            cats.append('Shopping')
        elif 'irctc' in m or 'makemytrip' in m or 'train' in m:
            cats.append('Travel')
        elif 'ola' in m or 'uber' in m:
            cats.append('Transport')
        elif 'jio' in m or 'recharge' in m:
            cats.append('Utilities')
        elif 'hdfc' in m or 'atm' in m:
            cats.append('Cash Withdrawal')
        elif 'bookmyshow' in m:
            cats.append('Entertainment')
        else:
            cats.append('Other')
    return cats


def classify_batch(records: List[Dict]) -> List[str]:
    """Classify a batch of records to categories.

    If Gemini is enabled and API key provided, sends a single batched prompt. Otherwise uses heuristic.
    """
    if USE_GEMINI and API_KEY:
        # Build a prompt that asks for a category for each merchant in order
        prompt_lines = [
            "Assign each transaction a single category from: Food, Shopping, Travel, Transport, Utilities, Cash Withdrawal, Entertainment, Other.",
            "Return a JSON array of categories in the same order as inputs."
        ]
        examples = []
        for r in records:
            examples.append(f"{r.get('merchant','')}: {r.get('notes','')} | amount: {r.get('amount')}")
        prompt = '\n'.join(prompt_lines + ['\n'.join(examples)])
        url = f"https://generativelanguage.googleapis.com/v1/{MODEL}:generateText?key={API_KEY}"
        payload = {"prompt": {"text": prompt}, "maxOutputTokens": 256}
        try:
            try:
                import requests
            except ImportError:
                requests = None
            if not requests:
                raise RuntimeError('requests not installed')
            resp = requests.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            text = data.get('candidates', [{}])[0].get('output', '') or data.get('output', '')
            # Attempt to parse a JSON array from the response
            import json
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return parsed[:len(records)]
            except Exception:
                # fallback: split lines and map
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                if len(lines) >= len(records):
                    return [lines[i] for i in range(len(records))]
        except Exception:
            pass
    return _heuristic_classify(records)


def generate_narrative(summary: Dict) -> Dict:
    """Generate a narrative summary from the summary dict. Returns a dict with narrative text.

    If Gemini enabled, call the API; otherwise create a simple local narrative.
    """
    if USE_GEMINI and API_KEY:
        prompt = (
            f"Given totals by currency: {summary.get('total_by_currency')}, top merchants: {summary.get('top_3_merchants')}, "
            f"and anomaly count {summary.get('anomaly_count')}, produce a JSON object with keys total_by_currency, top_3_merchants, anomaly_count, narrative (2-3 sentences)."
        )
        url = f"https://generativelanguage.googleapis.com/v1/{MODEL}:generateText?key={API_KEY}"
        payload = {"prompt": {"text": prompt}, "maxOutputTokens": 300}
        try:
            try:
                import requests
            except ImportError:
                requests = None
            if not requests:
                raise RuntimeError('requests not installed')
            resp = requests.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            text = data.get('candidates', [{}])[0].get('output', '') or data.get('output', '')
            import json
            try:
                parsed = json.loads(text)
                return parsed
            except Exception:
                return {'narrative': text}
        except Exception:
            pass

    # fallback local narrative
    tot = summary.get('total_by_currency', {})
    top = summary.get('top_3_merchants', [])
    narrative = f"Total spend: {', '.join([f'{v:.2f} {k}' for k,v in tot.items()])}. Top merchants: {', '.join(top)}."
    return {'narrative': narrative, 'total_by_currency': tot, 'top_3_merchants': top, 'anomaly_count': summary.get('anomaly_count', 0)}
