from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from uuid import uuid4
from pathlib import Path
from .. import crud
from ..models import JobStatus
from ..tasks import process_job

router = APIRouter(prefix="/jobs", tags=["jobs"])

STORAGE = Path(__file__).parent.parent.parent / "storage"
STORAGE.mkdir(exist_ok=True)


@router.post('/upload')
async def upload(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail='Only CSV allowed')
    job_id = str(uuid4())
    filename = STORAGE / f"{job_id}.csv"
    content = await file.read()
    filename.write_bytes(content)
    # create job record
    crud.create_job(job_id=job_id, filename=str(filename), status=JobStatus.PENDING)
    # enqueue the Celery task
    process_job.apply_async(args=(job_id, str(filename)))
    return JSONResponse({'job_id': job_id})


@router.get('/')
def list_jobs(status: str = None):
    jobs = crud.list_jobs(status=status)
    return jobs


@router.get('/{job_id}/status')
def job_status(job_id: str):
    job = crud.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='job not found')
    return job


@router.get('/{job_id}/results')
def job_results(job_id: str):
    job = crud.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='job not found')
    if job.get('status') != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail='job not completed')
    return crud.get_results(job_id)
