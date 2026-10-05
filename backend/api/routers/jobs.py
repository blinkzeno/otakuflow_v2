"""Job endpoints: list, detail with log tail, cooperative cancel."""

from fastapi import APIRouter, HTTPException

from backend.db.queries import jobs as job_queries
from backend.services import jobs as job_service

router = APIRouter()

TERMINAL = {"done", "failed", "cancelled", "paused"}


@router.get("/api/projects/{project_id}/jobs")
def list_project_jobs(project_id: int) -> list[dict]:
    return job_queries.list_jobs(project_id)


@router.get("/api/jobs/{job_id}")
def get_job(job_id: int) -> dict:
    job = job_queries.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    job["log_tail"] = job_service.read_log_tail(job_id)
    return job


@router.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: int) -> dict:
    job = job_queries.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job["status"] in TERMINAL:
        raise HTTPException(status_code=409, detail="job already finished")
    job_service.request_cancel(job_id)
    return {"status": "cancelling"}
