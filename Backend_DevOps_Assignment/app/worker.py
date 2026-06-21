import time
import sys
from pathlib import Path

# When running the worker as a script (python app/worker.py) the package imports
# may fail because the parent folder isn't on sys.path. Ensure the project root is
# available so `import app` works both when running as `python -m app.worker`
# and when running the file directly.
if __package__ is None:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))

from app import crud
from app.processor import process_file
from app.models import JobStatus


def poll_loop(poll_interval=2):
    while True:
        jobs = crud.list_jobs()
        for j in jobs:
            if j['status'] == JobStatus.PENDING:
                job_id = j['job_id']
                try:
                    crud.set_job_status(job_id, JobStatus.PROCESSING)
                    results, row_count = process_file(j['filename'])
                    crud.set_job_results(job_id, results, row_count=row_count)
                    crud.set_job_status(job_id, JobStatus.COMPLETED)
                except Exception as e:
                    crud.set_job_status(job_id, JobStatus.FAILED)
        time.sleep(poll_interval)


if __name__ == '__main__':
    try:
        print('Starting worker poll loop...')
        poll_loop()
    except KeyboardInterrupt:
        print('Worker stopped')
