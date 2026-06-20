#!/usr/bin/env python3
import time
import requests
import sys
import os
import json

API_HOST = os.getenv('API_HOST', 'http://api:8000')
SAMPLE_PATH = '/app/sample.csv'

def wait_for_api(timeout=60):
    start = time.time()
    url = f"{API_HOST}/jobs"
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=3)
            if r.status_code in (200, 204):
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def upload_and_poll():
    if not os.path.exists(SAMPLE_PATH):
        print('sample.csv not found at', SAMPLE_PATH)
        return 2
    files = {'file': open(SAMPLE_PATH, 'rb')}
    r = requests.post(f"{API_HOST}/jobs/upload", files=files)
    try:
        j = r.json()
    except Exception:
        print('Upload failed, status', r.status_code, r.text)
        return 3
    job_id = j.get('job_id')
    if not job_id:
        print('No job_id returned:', j)
        return 4
    print('Uploaded, job_id=', job_id)

    # poll
    while True:
        r = requests.get(f"{API_HOST}/jobs/{job_id}/status")
        if r.status_code == 200:
            s = r.json().get('status')
            print('status=', s)
            if s in ('COMPLETED', 'FAILED'):
                break
        else:
            print('Status request failed:', r.status_code, r.text)
        time.sleep(2)

    r = requests.get(f"{API_HOST}/jobs/{job_id}/results")
    if r.status_code == 200:
        try:
            data = r.json()
        except Exception:
            print('\nRESULTS (raw):\n')
            print(r.text)
            return 0

        # pretty print to stdout
        print('\nRESULTS:\n')
        print(json.dumps(data, indent=2))

        # small human summary
        cleaned = data.get('cleaned_transactions') or []
        anomalies = data.get('anomalies') or []
        categories = data.get('category_breakdown') or {}
        print('\nSUMMARY:')
        print(f"  transactions processed: {len(cleaned)}")
        print(f"  anomalies detected: {len(anomalies)}")
        print('  category breakdown:')
        for k, v in categories.items():
            print(f"    {k}: {v}")
        narrative = data.get('narrative')
        if narrative:
            print('\n  narrative:')
            if isinstance(narrative, dict):
                print(json.dumps(narrative, indent=2))
            else:
                print(str(narrative))

        # write pretty JSON to mounted output folder
        out_dir = '/app/output'
        out_path = os.path.join(out_dir, 'runner_output.json')
        try:
            os.makedirs(out_dir, exist_ok=True)
            with open(out_path, 'w') as f:
                json.dump(data, f, indent=2)
            print('\nWrote results to', out_path)
        except Exception as e:
            print('Failed to write results to output folder:', e)
        return 0
    else:
        print('Failed to get results:', r.status_code, r.text)
        return 5


if __name__ == '__main__':
    ok = wait_for_api(60)
    if not ok:
        print('API did not become ready')
        sys.exit(1)
    sys.exit(upload_and_poll())
