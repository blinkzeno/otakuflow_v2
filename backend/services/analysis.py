"""Chapter analysis: page batches in one vision call, then synthesis.

Pages already done are never sent again. One bad page never stops the
chapter. Every provider call is counted in ai_costs per model, so the
quota display stays exact. Heavy volume runs on the light high quota
model, narrative text tasks on the strong model with light fallback.
"""

import json
import logging
from collections.abc import Callable
from io import BytesIO

from PIL import Image

from backend.core import config
from backend.db.queries import costs as cost_queries
from backend.db.queries import pages as page_queries
from backend.db.queries import projects as project_queries
from backend.prompts import loader as prompt_loader
from backend.providers import gemini_vision
from backend.providers.base import ProviderError
from backend.services.jobs import JobCancelled, QuotaPaused, ai_backoff, ai_gate
from backend.storage import paths

logger = logging.getLogger("otakuflow")


def _payload(rel_path: str) -> bytes:
    source = paths.safe_join(*rel_path.split("/"))
    if not source.exists():
        raise ProviderError("invalid", f"image file missing: {rel_path}")
    with Image.open(source) as image:
        image.load()
    work = Image.open(source)
    work.thumbnail((1568, 1568))
    buffer = BytesIO()
    work.convert("RGB").save(buffer, "JPEG", quality=80)
    return buffer.getvalue()


VALID_PAGE_KINDS = {"story", "credits", "ad", "blank"}


def _clean_regions(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        return []
    cleaned: list[dict] = []
    for index, region in enumerate(raw, start=1):
        if not isinstance(region, dict):
            continue
        try:
            x, y, w, h = (float(region[key]) for key in ("x", "y", "w", "h"))
        except (KeyError, TypeError, ValueError):
            continue
        x, y = min(max(x, 0.0), 1000.0), min(max(y, 0.0), 1000.0)
        w, h = min(w, 1000.0 - x), min(h, 1000.0 - y)
        if w < 50 or h < 50:
            continue
        kind = "text" if region.get("kind") == "text" else "art"
        cleaned.append({"x": x, "y": y, "w": w, "h": h, "order": region.get("order", index), "kind": kind})
    return cleaned


def _clamp_importance(value: object) -> int:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0
    return max(0, min(10, number))


def _chunks(items: list, size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def analyze_chapter(
    chapter_id: int,
    progress: Callable[[int, int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> dict:
    report = progress or (lambda _done, _total: None)
    stop = should_stop or (lambda: False)
    prompt = prompt_loader.get("analyze_pages")
    model = config.vision_model()
    size = config.pages_per_call()
    pending = page_queries.pending_pages(chapter_id)
    total = len(pending)
    done = failed = 0
    position = 0
    for chunk in _chunks(pending, size):
        if stop():
            raise JobCancelled()
        ready: list[tuple[dict, bytes]] = []
        for page in chunk:
            position += 1
            try:
                ready.append((page, _payload(str(page["rel_path"]))))
            except ProviderError as exc:
                page_queries.update_analysis(
                    page["id"], status="failed", error=str(exc)[:300]
                )
                failed += 1
                report(position, total)
        if not ready:
            continue
        valid: list = []
        missing: list[int] = list(range(1, len(ready) + 1))
        retries = 0
        chunk_dead = False
        while True:
            ai_gate(model)
            try:
                valid, missing = gemini_vision.analyze_pages(
                    [raw for _, raw in ready], prompt, model
                )
                break
            except ProviderError as exc:
                if exc.kind == "rate_limit" and retries < 3:
                    retries += 1
                    ai_backoff(retries)
                    continue
                if exc.kind == "rate_limit":
                    raise QuotaPaused("daily vision quota reached, resume tomorrow")
                if exc.kind == "network" and retries < 2:
                    retries += 1
                    ai_backoff(retries)
                    continue
                base = position - len(ready)
                for slot, (page, _) in enumerate(ready, start=1):
                    page_queries.update_analysis(
                        page["id"], status="failed", error=str(exc)[:300]
                    )
                    failed += 1
                    report(base + slot, total)
                chunk_dead = True
                break
        if chunk_dead:
            cost_queries.log_call(
                chapter_id, "gemini", model, "vision", {"images": len(ready)}
            )
            continue
        by_index = {item.batch_index: item for item in valid}
        for slot, (page, _) in enumerate(ready, start=1):
            item = by_index.get(slot)
            if item is None:
                page_queries.update_analysis(
                    page["id"], status="failed", error="bad batch_index"
                )
                failed += 1
            else:
                data = item.model_dump()
                data["focus_regions"] = _clean_regions(data.get("focus_regions"))
                if data.get("page_kind") not in VALID_PAGE_KINDS:
                    data["page_kind"] = "story"
                page_queries.update_analysis(
                    page["id"],
                    analysis_json=json.dumps(data, ensure_ascii=False),
                    importance=_clamp_importance(item.importance),
                    status="done",
                )
                done += 1
            report(position - len(ready) + slot, total)
        cost_queries.log_call(
            chapter_id, "gemini", model, "vision", {"images": len(ready)}
        )
    logger.info("[analysis] chapter=%s done=%s failed=%s", chapter_id, done, failed)
    return {"done": done, "failed": failed}


def _with_fallback(kind: str, prompt: str, payload: str):
    """Strong model first, light model once when the strong one pauses."""
    strong = config.text_model()
    light = config.vision_model()
    models = [strong] if strong == light else [strong, light]
    for position, model in enumerate(models):
        ai_gate(model)
        try:
            if kind == "synthesis":
                return gemini_vision.synthesize(payload, prompt, model), model
            return gemini_vision.generate_script(payload, prompt, model), model
        except ProviderError as exc:
            if exc.kind == "rate_limit" and position < len(models) - 1:
                logger.warning("[ai] strong model paused, fallback to light")
                continue
            if exc.kind == "rate_limit":
                raise QuotaPaused("daily vision quota reached, resume tomorrow")
            raise
    raise QuotaPaused("daily vision quota reached, resume tomorrow")


def synthesize_chapter(chapter_id: int) -> dict:
    chapter = project_queries.get_chapter(chapter_id)
    if chapter is None:
        raise ValueError("chapter not found")
    pages = [
        page
        for page in page_queries.list_pages(chapter_id)
        if page["analysis_status"] == "done" and page["analysis_json"]
    ]
    if not pages:
        raise ValueError("no analyzed page to synthesize")
    blob = "\n".join(
        f"[page {page['page_index']}] {page['analysis_json']}" for page in pages
    )[:12000]
    prompt = prompt_loader.get("synthesize_chapter")
    try:
        summary, model = _with_fallback("synthesis", prompt, blob)
    except ProviderError as exc:
        raise ValueError(str(exc)[:300])
    project_queries.update_chapter_summary(chapter_id, summary.model_dump_json())
    cost_queries.log_call(
        chapter_id, "gemini", model, "synthesis", {"pages": len(pages)}
    )
    return {"pages": len(pages)}
