from fastapi import FastAPI
from .routers import jobs

app = FastAPI(title="Transaction Processing API")
app.include_router(jobs.router)
