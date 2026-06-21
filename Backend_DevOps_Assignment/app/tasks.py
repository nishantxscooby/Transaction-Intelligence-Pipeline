from .celery_app import celery, CELERY_AVAILABLE
from . import crud
from .processor import process_file
from .models import JobStatus


def _process_job_impl(job_id, filename):
    try:
        crud.set_job_status(job_id, JobStatus.PROCESSING)
        results, row_count = process_file(filename)
        crud.set_job_results(job_id, results, row_count=row_count)
        crud.set_job_status(job_id, JobStatus.COMPLETED)
        return {'status': 'ok', 'rows': row_count}
    except Exception as e:
        crud.set_job_status(job_id, JobStatus.FAILED)
        return {'status': 'error', 'error': str(e)}


if CELERY_AVAILABLE and celery is not None:
    @celery.task(name='process_job')
    def process_job(job_id, filename):
        return _process_job_impl(job_id, filename)
else:
    def process_job(job_id, filename):
        # direct call when Celery isn't available
        return _process_job_impl(job_id, filename)
