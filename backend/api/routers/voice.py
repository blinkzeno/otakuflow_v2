"""Voice endpoints: batch synthesis as a job, single regen, MP3 bytes."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.db.queries import audio as audio_queries
from backend.db.queries import projects as project_queries
from backend.db.queries import segments as segment_queries
from backend.services import jobs as job_service
from backend.services import tts as tts_service
from backend.storage import paths

router = APIRouter()

AUDIO_MEDIA = {
    ".mp3": "audio/mpeg",
}


@router.post("/api/chapters/{chapter_id}/voice", status_code=202)
def synthesize_voices(chapter_id: int) -> dict:
    from backend.db.queries import jobs as job_queries

    chapter = project_queries.get_chapter(chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="chapter not found")
    if segment_queries.has_draft(chapter_id):
        raise HTTPException(
            status_code=422, detail="script not reviewed, lock it first"
        )
    job_id = job_queries.create_job(chapter["project_id"], "tts")
    job_service.enqueue(
        chapter["project_id"], job_id, tts_service.ensure_voices, chapter_id
    )
    return {"chapter_id": chapter_id, "job_id": job_id}


@router.post("/api/segments/{segment_key}/voice")
def regenerate_voice(segment_key: str) -> dict:
    try:
        return tts_service.regenerate_one(segment_key)
    except ValueError as exc:
        message = str(exc)
        raise HTTPException(
            status_code=404 if "not found" in message else 422, detail=message
        )


@router.get("/api/segments/{segment_key}/audio")
def get_audio(segment_key: str) -> FileResponse:
    segment = segment_queries.get_by_key(segment_key)
    if segment is None:
        raise HTTPException(status_code=404, detail="segment not found")
    audio = audio_queries.get_by_segment(segment["id"])
    if audio is None:
        raise HTTPException(status_code=404, detail="no audio yet, synthesize first")
    file_path = paths.safe_join(*str(audio["rel_path"]).split("/"))
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="audio file missing")
    return FileResponse(
        file_path,
        media_type=AUDIO_MEDIA.get(file_path.suffix.lower(), "audio/mpeg"),
    )
