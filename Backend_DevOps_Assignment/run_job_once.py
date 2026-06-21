from app import crud
from app.processor import process_file
from uuid import uuid4

JOB_ID = str(uuid4())
FNAME = 'transactions.csv'

crud.create_job(JOB_ID, FNAME)
print('Created job', JOB_ID)
results, row_count = process_file(FNAME)
crud.set_job_results(JOB_ID, results, row_count=row_count)
crud.set_job_status(JOB_ID, 'COMPLETED')
print('Job completed, rows:', row_count)
print('Summary keys:', list(results.keys()))
