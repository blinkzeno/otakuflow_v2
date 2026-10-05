"""Render endpoints: launch, preview the derived timeline, fetch MP4."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.db.queries import projects as project_queries
from backend.db.queries import renders as render_queries
from backend.db.queries import segments as segment_queries
from backend.services import jobs as job_service
from backend.services import timeline as timeline_service
from backend.services import video as video_service
from backend.storage import paths

router = APIRouter()


@router.post("/api/chapters/{chapter_id}/render", status_code=202)
def render_chapter(chapter_id: int, body: dict | None = None) -> dict:
    from backend.db.queries import jobs as job_queries

    chapter = project_queries.get_chapter(chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="chapter not found")
    if segment_queries.has_draft(chapter_id):
        raise HTTPException(
            status_code=422, detail="script not reviewed, lock it first"
        )
    try:
        settings = video_service.validate_settings((body or {}).get("settings"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    try:
        timeline_service.build_timeline(chapter_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    job_id = job_queries.create_job(chapter["project_id"], "render")
    job_service.enqueue(
        chapter["project_id"],
        job_id,
        video_service.render_chapter,
        chapter_id,
        settings,
    )
    return {"chapter_id": chapter_id, "job_id": job_id}


@router.get("/api/chapters/{chapter_id}/timeline")
def get_timeline(chapter_id: int) -> dict:
    chapter = project_queries.get_chapter(chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="chapter not found")
    try:
        clips = timeline_service.build_timeline(chapter_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"clips": clips, "total": timeline_service.timeline_total(clips)}


@router.get("/api/chapters/{chapter_id}/render/latest")
def get_latest_render(chapter_id: int) -> dict | None:
    chapter = project_queries.get_chapter(chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="chapter not found")
    return render_queries.latest_render(chapter_id)


@router.get("/api/renders/{render_id}/video")
def get_video(render_id: int) -> FileResponse:
    render = render_queries.get_render(render_id)
    if render is None or not render.get("video_rel_path"):
        raise HTTPException(status_code=404, detail="video not found")
    file_path = paths.safe_join(*str(render["video_rel_path"]).split("/"))
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="video file missing")
    return FileResponse(
        file_path,
        media_type="video/mp4",
        filename=f"otakuflow_chapter_{render['chapter_id']}.mp4",
    )
