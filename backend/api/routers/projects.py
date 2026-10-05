"""Project endpoints: list, create from upload, detail, delete, retry."""

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.db.queries import jobs as job_queries
from backend.db.queries import pages as page_queries
from backend.db.queries import projects as project_queries
from backend.services import ingestion, jobs as job_service
from backend.storage import paths

router = APIRouter()

ALLOWED_UPLOAD_SUFFIXES = {".cbz", ".zip"}


@router.get("/api/projects")
def list_projects() -> list[dict]:
    return project_queries.list_projects()


@router.post("/api/projects", status_code=202)
async def create_project(
    file: UploadFile = File(...), title: str = Form(...)
) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        raise HTTPException(status_code=422, detail="only .cbz or .zip uploads")
    tmp_name = f"upload_{uuid.uuid4().hex}{suffix}"
    tmp_path = paths.safe_join("tmp", tmp_name)
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(tmp_path, "wb") as disk:
            while chunk := await file.read(1024 * 1024):
                disk.write(chunk)
    finally:
        await file.close()
    try:
        ids = ingestion.begin_import(title, file.filename or tmp_name)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="could not start import")
    job_service.enqueue(
        ids["project_id"],
        ids["job_id"],
        ingestion.ingest_upload,
        str(tmp_path),
        file.filename or tmp_name,
        title,
        ids=ids,
    )
    return {"project_id": ids["project_id"], "job_id": ids["job_id"]}


@router.post("/api/projects/{project_id}/retry-import", status_code=202)
def retry_import(project_id: int) -> dict:
    project = project_queries.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    try:
        replay = ingestion.retry_import(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    ids = replay["ids"]
    job_service.enqueue(
        ids["project_id"],
        ids["job_id"],
        ingestion.ingest_upload,
        replay["tmp"],
        project_queries.get_chapter(ids["chapter_id"])["source_filename"],
        replay["title"],
        ids=replay["ids"],
    )
    return {"project_id": project_id, "job_id": ids["job_id"]}


@router.get("/api/projects/{project_id}")
def get_project(project_id: int) -> dict:
    project = project_queries.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    chapters = project_queries.list_chapters(project_id)
    jobs = job_queries.list_jobs(project_id)
    return {"project": project, "chapters": chapters, "jobs": jobs}


@router.delete("/api/projects/{project_id}")
def delete_project(project_id: int) -> dict:
    project = project_queries.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    project_queries.delete_project(project_id)
    try:
        shutil.rmtree(paths.project_dir(project_id))
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"files not removed: {exc}")
    return {"deleted": project_id}


@router.get("/api/chapters/{chapter_id}/pages")
def list_chapter_pages(chapter_id: int) -> list[dict]:
    chapter = project_queries.get_chapter(chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="chapter not found")
    return page_queries.list_pages(chapter_id)
