"""Narration script: generate from analysis, edit, lock for voice.

Positions and keys are always dense and derived from order. Any text or
page change sends the segment back to draft. Voice (007) refuses chapters
that still hold drafts.
"""

import json
import logging
import re

from pydantic import BaseModel, ValidationError, ValidationError

from backend.core import config
from backend.db.queries import costs as cost_queries
from backend.db.queries import pages as page_queries
from backend.db.queries import projects as project_queries
from backend.db.queries import segments as segment_queries
from backend.prompts import loader as prompt_loader
from backend.providers import gemini_vision
from backend.providers.base import ProviderError
from backend.services.jobs import QuotaPaused, ai_backoff, ai_gate

logger = logging.getLogger("otakuflow")

CHARS_PER_MINUTE = 900
PAYLOAD_MAX_CHARS = 120000

PAGE_MENTION_RE = re.compile(
    r"\bpages?\s+\d+|\bon\s+pages?\b|\bpanels?\s+\d+|\bin\s+panels?\b|\bchapter\s+\d+",
    re.IGNORECASE,
)


class _RepairOut(BaseModel):
    texts: list[str]


def _call_text_model(call_fn):
    """Run a text provider call on strong then light. Returns (result, model)."""
    strong = config.text_model()
    light = config.vision_model()
    models = [strong] if strong == light else [strong, light]
    retries = 0
    for rank, model in enumerate(models):
        while True:
            ai_gate(model)
            try:
                return call_fn(model), model
            except ProviderError as exc:
                if exc.kind == "rate_limit" and rank < len(models) - 1:
                    logger.warning("[script] strong model paused, fallback to light")
                    break
                if exc.kind == "rate_limit":
                    raise QuotaPaused("daily vision quota reached, resume tomorrow")
                if exc.kind == "network" and retries < 2:
                    retries += 1
                    ai_backoff(retries)
                    continue
                raise ValueError(str(exc)[:300])
    raise QuotaPaused("daily vision quota reached, resume tomorrow")


def _repair_texts(texts: list[str]) -> tuple[list[str], str]:
    """Rewrite narration segments without any page mention. One call."""
    prompt = (
        "Rewrite each of these voiceover narration segments with the same "
        "meaning and about the same length, but remove every mention of "
        "pages, page numbers or panels. Keep all names, events and visual "
        'details. Answer JSON: {"texts": [...]} in the same order.'
    )
    payload = json.dumps(texts)

    def call(model: str) -> list[str]:
        raw = gemini_vision.complete_json(
            f"{prompt}\n\nSegments:\n{payload}",
            _RepairOut.model_json_schema(),
            model,
        )
        try:
            parsed = _RepairOut.model_validate_json(raw)
        except ValidationError:
            retry = gemini_vision.complete_json(
                f"{prompt}\nReturn valid JSON only.\n\nSegments:\n{payload}",
                _RepairOut.model_json_schema(),
                model,
            )
            parsed = _RepairOut.model_validate_json(retry)
        if len(parsed.texts) != len(texts):
            raise ValueError("repair changed segment count")
        return parsed.texts

    return _call_text_model(call)


def _estimate_seconds(text: str) -> float:
    return round(len(text) / CHARS_PER_MINUTE * 60, 1)


def _key(chapter_id: int, position: int) -> str:
    return f"ch{chapter_id}_s{position:03d}"


def reindex(chapter_id: int) -> None:
    ordered = segment_queries.list_ordered(chapter_id)
    for position, segment in enumerate(ordered, start=1):
        if segment["position"] != position:
            segment_queries.update_segment(segment["id"], position=position)
        want = _key(chapter_id, position)
        if segment["segment_key"] != want:
            segment_queries.update_key(segment["id"], want)


def generate(chapter_id: int, confirm_overwrite: bool = False) -> dict:
    chapter = project_queries.get_chapter(chapter_id)
    if chapter is None:
        raise ValueError("chapter not found")
    pages = page_queries.list_pages(chapter_id)
    if not pages:
        raise ValueError("chapter has no page")
    done_pages = [page for page in pages if page["analysis_status"] == "done"]
    if len(done_pages) < len(pages) / 2:
        raise ValueError("analysis too thin, analyze pages first")
    existing = segment_queries.list_ordered(chapter_id)
    kept = [seg for seg in existing if seg["status"] in ("reviewed", "voiced")]
    if kept and not confirm_overwrite:
        base_position = max(seg["position"] for seg in kept)
        segment_queries.delete_by_status(chapter_id, "draft")
    elif confirm_overwrite:
        segment_queries.delete_all(chapter_id)
        kept = []
        base_position = 0
    else:
        base_position = 0
    blob = {
        "page_count": len(pages),
        "summary": chapter.get("chapter_summary"),
        "pages": [
            {"index": page["page_index"], "analysis": page["analysis_json"]}
            for page in done_pages
        ],
    }
    payload = json.dumps(blob)
    if len(payload) > PAYLOAD_MAX_CHARS:
        ranked = sorted(
            done_pages, key=lambda p: (p.get("importance") or 0), reverse=True
        )
        keep = max(len(done_pages) // 2, 1)
        kept_indexes = {p["page_index"] for p in ranked[:keep]}
        blob["pages"] = [entry for entry in blob["pages"] if entry["index"] in kept_indexes]
        blob["truncated"] = True
        payload = json.dumps(blob)[:PAYLOAD_MAX_CHARS]
        logger.warning(
            "[script] truncated %s low importance pages for chapter %s",
            len(done_pages) - keep,
            chapter_id,
        )
    prompt = prompt_loader.get("generate_script")
    draft, used_model = _call_text_model(
        lambda model: gemini_vision.generate_script(payload, prompt, model)
    )
    assert draft is not None
    bad = [
        position
        for position, seg in enumerate(draft.segments)
        if PAGE_MENTION_RE.search(seg.text)
    ]
    if bad:
        logger.info("[script] repairing %s segments with page mentions", len(bad))
        try:
            fixed, repair_model = _repair_texts(
                [draft.segments[position].text for position in bad]
            )
        except QuotaPaused:
            raise
        except (ProviderError, ValueError, ValidationError):
            raise ValueError(
                f"page mention repair failed for segments {[p + 1 for p in bad]}"
            )
        for position, text in zip(bad, fixed):
            draft.segments[position].text = text
        cost_queries.log_call(
            chapter_id, "gemini", repair_model, "script_repair",
            {"segments": len(bad)},
        )
        still = [
            position + 1
            for position, seg in enumerate(draft.segments)
            if PAGE_MENTION_RE.search(seg.text)
        ]
        if still:
            raise ValueError(f"page mention survives in segments {still}")
        logger.info("[script] repaired %s segments", len(bad))
    valid_indexes = {page["page_index"] for page in pages}
    rows = []
    for offset, seg in enumerate(draft.segments, start=1):
        refs = [idx for idx in seg.page_refs if idx in valid_indexes]
        position = base_position + offset
        rows.append(
            {
                "position": position,
                "segment_key": _key(chapter_id, position),
                "text": seg.text.strip(),
                "page_refs": json.dumps(refs),
                "duration_estimate": _estimate_seconds(seg.text),
                "status": "draft",
            }
        )
    if not rows:
        raise ValueError("model returned no segment")
    segment_queries.insert_many(chapter_id, rows)
    cost_queries.log_call(
        chapter_id, "gemini", used_model, "script",
        {"segments": len(rows)},
    )
    logger.info("[script] chapter=%s segments=%s", chapter_id, len(rows))
    return {"segments": len(rows)}


def _split_text(text: str) -> tuple[str, str]:
    parts = [part for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part]
    if len(parts) < 2:
        half = max(1, len(text) // 2)
        return text[:half].rstrip(), text[half:].lstrip()
    total = sum(len(part) for part in parts)
    running = 0
    for cut in range(1, len(parts)):
        running += len(parts[cut - 1])
        if running >= total / 2:
            return " ".join(parts[:cut]), " ".join(parts[cut:])
    return parts[0], " ".join(parts[1:])


def split_segment(segment_key: str) -> dict:
    segment = segment_queries.get_by_key(segment_key)
    if segment is None:
        raise ValueError("segment not found")
    first, second = _split_text(segment["text"])
    refs = segment["page_refs"]
    segment_queries.update_segment(
        segment["id"], text=first, page_refs=refs, status="draft"
    )
    segment_queries.insert_many(
        segment["chapter_id"],
        [
            {
                "position": segment["position"] + 1,
                "segment_key": _key(segment["chapter_id"], segment["position"] + 1)
                + "_tmp",
                "text": second,
                "page_refs": refs,
                "duration_estimate": _estimate_seconds(second),
                "status": "draft",
            }
        ],
    )
    reindex(segment["chapter_id"])
    return {"split": segment_key}


def merge_next(segment_key: str) -> dict:
    segment = segment_queries.get_by_key(segment_key)
    if segment is None:
        raise ValueError("segment not found")
    ordered = segment_queries.list_ordered(segment["chapter_id"])
    ids = [seg["id"] for seg in ordered]
    position = ids.index(segment["id"])
    if position >= len(ordered) - 1:
        raise ValueError("no next segment to merge")
    follower = ordered[position + 1]
    pages = json.loads(segment["page_refs"]) + [
        idx for idx in json.loads(follower["page_refs"])
        if idx not in json.loads(segment["page_refs"])
    ]
    text = (segment["text"].rstrip() + " " + follower["text"].lstrip()).strip()
    segment_queries.update_segment(
        segment["id"],
        text=text,
        page_refs=json.dumps(pages),
        duration_estimate=_estimate_seconds(text),
        status="draft",
    )
    segment_queries.delete_segment(follower["id"])
    reindex(segment["chapter_id"])
    return {"merged": segment_key}


def patch_segment(
    segment_key: str,
    text: str | None = None,
    page_refs: list[int] | None = None,
    position: int | None = None,
) -> dict:
    segment = segment_queries.get_by_key(segment_key)
    if segment is None:
        raise ValueError("segment not found")
    fields: dict = {}
    if text is not None:
        fields["text"] = text.strip()
        fields["duration_estimate"] = _estimate_seconds(text)
    if page_refs is not None:
        pages = page_queries.list_pages(segment["chapter_id"])
        valid = {page["page_index"] for page in pages}
        fields["page_refs"] = json.dumps([idx for idx in page_refs if idx in valid])
    if position is not None:
        fields["position"] = max(1, int(position))
    if "text" in fields or "page_refs" in fields:
        fields["status"] = "draft"
    if fields:
        segment_queries.update_segment(segment["id"], **fields)
    if position is not None:
        reindex(segment["chapter_id"])
    ordered = segment_queries.list_ordered(segment["chapter_id"])
    updated = next((seg for seg in ordered if seg["id"] == segment["id"]), None)
    return updated or {}


def delete_segment(segment_key: str) -> dict:
    segment = segment_queries.get_by_key(segment_key)
    if segment is None:
        raise ValueError("segment not found")
    segment_queries.delete_segment(segment["id"])
    reindex(segment["chapter_id"])
    return {"deleted": segment_key}


def mark_reviewed(chapter_id: int) -> dict:
    count = segment_queries.mark_reviewed(chapter_id)
    return {"reviewed": count}
