"""Voice over: one MP3 per reviewed segment, hash driven regen.

A segment is re synthesized only when its text changed since its audio.
Anything else is skipped with zero network call. One bad segment never
stops the chapter, it stays reviewed for a single retry.
"""

import hashlib
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mutagen.mp3 import MP3

from backend.core import config
from backend.db.queries import audio as audio_queries
from backend.db.queries import segments as segment_queries
from backend.providers import edge_tts
from backend.services.jobs import JobCancelled
from backend.storage import paths

logger = logging.getLogger("otakuflow")


def _default_synthesize(text: str, voice: str) -> bytes:
    return edge_tts.synthesize(text, voice)


def _default_duration(path: Path) -> float:
    info = MP3(path).info
    return float(info.length) if info else 0.0


synthesize_fn: Callable[[str, str], bytes] = _default_synthesize
duration_fn: Callable[[Path], float] = _default_duration


def text_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def _audio_filename(segment_id: int) -> str:
    return f"sg_{segment_id:04d}.mp3"


def _render_one(segment: dict, voice: str) -> dict[str, Any]:
    raw = synthesize_fn(segment["text"], voice)
    target = paths.audio_path(segment["project_id"], _audio_filename(segment["id"]))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    duration = duration_fn(target)
    if duration <= 0:
        target.unlink(missing_ok=True)
        raise ValueError("invalid audio duration")
    row = {
        "provider": "edge",
        "voice": voice,
        "rel_path": f"projects/{segment['project_id']}/audio/{target.name}",
        "duration": duration,
        "text_hash": text_hash(segment["text"]),
    }
    audio_queries.upsert_audio(segment["id"], row)
    segment_queries.update_segment(segment["id"], status="voiced")
    return {"duration": duration}


def ensure_voices(
    chapter_id: int,
    progress: Callable[[int, int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> dict:
    report = progress or (lambda _done, _total: None)
    stop = should_stop or (lambda: False)
    if segment_queries.has_draft(chapter_id):
        raise ValueError("script not reviewed, run /script/review first")
    from backend.db.queries import projects as project_queries

    chapter = project_queries.get_chapter(chapter_id)
    if chapter is None:
        raise ValueError("chapter not found")
    project_id = int(chapter["project_id"])
    voice = config.tts_voice()
    targets = [
        seg
        for seg in segment_queries.list_ordered(chapter_id)
        if seg["status"] in ("reviewed", "voiced")
    ]
    total = len(targets)
    voiced = skipped = failed = 0
    for position, segment in enumerate(targets, start=1):
        if stop():
            raise JobCancelled()
        existing = audio_queries.get_by_segment(segment["id"])
        if (
            existing
            and existing["text_hash"] == text_hash(segment["text"])
            and paths.safe_join(*str(existing["rel_path"]).split("/")).exists()
        ):
            skipped += 1
            report(position, total)
            continue
        try:
            segment["project_id"] = project_id
            _render_one(segment, voice)
            voiced += 1
        except Exception as exc:
            failed += 1
            logger.warning(
                "[tts] segment %s failed: %s", segment["segment_key"], exc
            )
        report(position, total)
    logger.info(
        "[tts] chapter=%s voiced=%s skipped=%s failed=%s",
        chapter_id,
        voiced,
        skipped,
        failed,
    )
    return {"voiced": voiced, "skipped": skipped, "failed": failed}


def regenerate_one(segment_key: str) -> dict:
    from backend.db.queries import projects as project_queries

    segment = segment_queries.get_by_key(segment_key)
    if segment is None:
        raise ValueError("segment not found")
    chapter = project_queries.get_chapter(segment["chapter_id"])
    if chapter is None:
        raise ValueError("chapter not found")
    segment["project_id"] = int(chapter["project_id"])
    result = _render_one(segment, config.tts_voice())
    return {"duration": result["duration"]}
