"""Analysis endpoints: run vision, synthesize, read quota."""

from fastapi import APIRouter, HTTPException

from backend.core import config
from backend.db.queries import costs as cost_queries
from backend.db.queries import projects as project_queries
from backend.services import analysis, jobs as job_service

router = APIRouter()


@router.post("/api/chapters/{chapter_id}/analyze", status_code=202)
def analyze_chapter(chapter_id: int) -> dict:
    from backend.db.queries import jobs as job_queries

    chapter = project_queries.get_chapter(chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="chapter not found")
    job_id = job_queries.create_job(chapter["project_id"], "analyze")
    job_service.enqueue(
        chapter["project_id"], job_id, analysis.analyze_chapter, chapter_id
    )
    return {"chapter_id": chapter_id, "job_id": job_id}


@router.post("/api/chapters/{chapter_id}/synthesize")
def synthesize_chapter(chapter_id: int) -> dict:
    from backend.services.jobs import QuotaPaused

    chapter = project_queries.get_chapter(chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="chapter not found")
    try:
        return analysis.synthesize_chapter(chapter_id)
    except QuotaPaused as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/api/quota")
def get_quota() -> dict:
    vision = config.vision_model()
    text_model = config.text_model()
    return {
        "vision": {
            "model": vision,
            "used": cost_queries.calls_today_for_model(vision),
            "cap": config.daily_cap(),
        },
        "text": {
            "model": text_model,
            "used": cost_queries.calls_today_for_model(text_model),
            "cap": config.text_daily_cap(),
        },
    }
