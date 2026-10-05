"""Script endpoints: generate, edit, lock, export."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.db.queries import projects as project_queries
from backend.db.queries import segments as segment_queries
from backend.services import script as script_service
from backend.services.jobs import QuotaPaused

router = APIRouter()


def _chapter_or_404(chapter_id: int) -> dict:
    chapter = project_queries.get_chapter(chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="chapter not found")
    return chapter


@router.post("/api/chapters/{chapter_id}/script")
def generate_script(chapter_id: int, body: dict | None = None) -> dict:
    _chapter_or_404(chapter_id)
    confirm = bool((body or {}).get("confirm_overwrite"))
    try:
        return script_service.generate(chapter_id, confirm_overwrite=confirm)
    except QuotaPaused as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/api/chapters/{chapter_id}/script")
def list_script(chapter_id: int) -> list[dict]:
    _chapter_or_404(chapter_id)
    return segment_queries.list_ordered(chapter_id)


@router.patch("/api/segments/{segment_key}")
def patch_segment(segment_key: str, body: dict) -> dict:
    allowed = {"text", "page_refs", "position"}
    if not any(key in body for key in allowed):
        raise HTTPException(status_code=422, detail="nothing to update")
    refs = body.get("page_refs")
    if refs is not None and (
        not isinstance(refs, list) or not all(isinstance(i, int) for i in refs)
    ):
        raise HTTPException(status_code=422, detail="page_refs must be ints")
    try:
        return script_service.patch_segment(
            segment_key,
            text=body.get("text"),
            page_refs=refs,
            position=body.get("position"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/api/segments/{segment_key}/split")
def split_segment(segment_key: str) -> dict:
    try:
        return script_service.split_segment(segment_key)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/api/segments/{segment_key}/merge")
def merge_segment(segment_key: str) -> dict:
    try:
        return script_service.merge_next(segment_key)
    except ValueError as exc:
        message = str(exc)
        raise HTTPException(
            status_code=404 if "not found" in message else 422, detail=message
        )


@router.delete("/api/segments/{segment_key}")
def delete_segment(segment_key: str) -> dict:
    try:
        return script_service.delete_segment(segment_key)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/api/chapters/{chapter_id}/script/review")
def review_script(chapter_id: int) -> dict:
    _chapter_or_404(chapter_id)
    return script_service.mark_reviewed(chapter_id)


@router.get("/api/chapters/{chapter_id}/script/export")
def export_script(chapter_id: int) -> JSONResponse:
    chapter = _chapter_or_404(chapter_id)
    segments = segment_queries.list_ordered(chapter_id)
    payload = {
        "chapter": chapter["title"],
        "segments": [
            {
                "position": seg["position"],
                "text": seg["text"],
                "pages": seg["page_refs"],
                "status": seg["status"],
            }
            for seg in segments
        ],
    }
    return JSONResponse(
        content=payload,
        headers={
            "Content-Disposition": (
                f"attachment; filename=chapter_{chapter_id}_script.json"
            )
        },
    )
