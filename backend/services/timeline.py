"""Render timeline derived from real audio durations only.

No estimated duration ever enters the timeline. A segment without a
valid audio blocks the render with a clear message instead of producing
a silent video. Each page carries its focus box when the analysis has
one, so the renderer can frame what matters.
"""

import json
import logging

from backend.db.queries import audio as audio_queries
from backend.db.queries import pages as page_queries
from backend.db.queries import segments as segment_queries

logger = logging.getLogger("otakuflow")


def page_focus(page: dict) -> dict | None:
    """Focus box {x, y, w, h} in 0-1000, or None for full frame."""
    try:
        analysis = json.loads(page.get("analysis_json") or "{}")
    except (ValueError, TypeError):
        return None
    focus = analysis.get("focus") or {}
    try:
        box = {
            "x": int(focus.get("x", 0)),
            "y": int(focus.get("y", 0)),
            "w": int(focus.get("w", 1000)),
            "h": int(focus.get("h", 1000)),
        }
    except (TypeError, ValueError):
        return None
    if box["w"] <= 0 or box["h"] <= 0:
        return None
    if box == {"x": 0, "y": 0, "w": 1000, "h": 1000}:
        return None
    for key in ("x", "y"):
        box[key] = max(0, min(1000, box[key]))
    box["w"] = max(1, min(1000 - box["x"], box["w"]))
    box["h"] = max(1, min(1000 - box["y"], box["h"]))
    return box


def page_regions(page: dict) -> list[dict]:
    """Ordered focus regions, cleaned. Empty list when absent."""
    try:
        analysis = json.loads(page.get("analysis_json") or "{}")
    except (ValueError, TypeError):
        return []
    raw = analysis.get("focus_regions")
    if not isinstance(raw, list):
        return []
    regions: list[dict] = []
    for region in raw:
        if not isinstance(region, dict):
            continue
        try:
            box = {key: float(region.get(key, 0)) for key in ("x", "y", "w", "h")}
        except (TypeError, ValueError):
            continue
        order = region.get("order", 0)
        try:
            order = int(order)
        except (TypeError, ValueError):
            order = 0
        kind = "text" if region.get("kind") == "text" else "art"
        regions.append({**box, "order": order, "kind": kind})
    return sorted(regions, key=lambda item: item["order"])


def page_kind_of(page: dict) -> str:
    """Kind of page (story by default, retrocompatible)."""
    try:
        analysis = json.loads(page.get("analysis_json") or "{}")
    except (ValueError, TypeError):
        return "story"
    kind = analysis.get("page_kind")
    return kind if kind in ("story", "credits", "ad", "blank") else "story"


def build_timeline(chapter_id: int) -> list[dict]:
    segments = [
        seg
        for seg in segment_queries.list_ordered(chapter_id)
        if seg["status"] in ("reviewed", "voiced")
    ]
    if not segments:
        raise ValueError("no voiced segment to render")
    pages = page_queries.list_pages(chapter_id)
    if not pages:
        raise ValueError("chapter has no page")
    by_index = {page["page_index"]: page for page in pages}
    fallback = pages[0]
    clips: list[dict] = []
    cursor = 0.0
    for segment in segments:
        audio = audio_queries.get_by_segment(segment["id"])
        if audio is None or float(audio["duration"]) <= 0:
            raise ValueError(f"segment {segment['segment_key']} has no audio")
        refs = json.loads(segment["page_refs"])
        chosen = [by_index[i] for i in refs if i in by_index] or [fallback]
        if not refs:
            logger.warning(
                "[timeline] segment %s cites no page, using first",
                segment["segment_key"],
            )
        duration = round(float(audio["duration"]), 3)
        clips.append(
            {
                "segment_key": segment["segment_key"],
                "position": segment["position"],
                "start": round(cursor, 3),
                "duration": duration,
                "audio_rel": str(audio["rel_path"]),
                "pages": [
                    {
                        "id": page["id"],
                        "index": page["page_index"],
                        "focus": page_focus(page),
                        "focus_regions": page_regions(page),
                        "page_kind": page_kind_of(page),
                    }
                    for page in chosen
                ],
            }
        )
        cursor += duration
    if cursor <= 0:
        raise ValueError("empty timeline")
    return clips


def timeline_total(clips: list[dict]) -> float:
    return round(sum(clip["duration"] for clip in clips), 3)
