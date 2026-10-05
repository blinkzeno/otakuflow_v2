"""CBZ and ZIP ingestion: safe extract, numeric sort, page indexation.

Original upload is kept untouched under originals. Normalized JPEG pages
go under pages, small thumbs under thumbs. One corrupt image never stops
the chapter, it is counted as skipped.

Runs inside the jobs worker: reports progress, honors cancel between
pages, cleans up its own mess on failure. begin_import creates the fast
skeleton rows so POST can answer 202 at once. retry_import replays a
chapter from the kept originals, no reupload needed.
"""

import logging
import shutil
import uuid
import zipfile
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

from backend.core import config
from backend.core.sort import natural_key
from backend.db.queries import jobs as job_queries
from backend.db.queries import pages as page_queries
from backend.db.queries import projects as project_queries
from backend.services.jobs import JobCancelled
from backend.storage import paths

logger = logging.getLogger("otakuflow")

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _is_usable_member(name: str) -> bool:
    flat = name.replace("\\", "/")
    if flat.startswith("__MACOSX/") or "/__MACOSX/" in flat:
        return False
    base = flat.rsplit("/", 1)[-1]
    if base.startswith("."):
        return False
    return Path(base).suffix.lower() in IMAGE_SUFFIXES


def _normalize_image(raw: bytes) -> Image.Image:
    with Image.open(BytesIO(raw)) as probe:
        probe.load()
    image = Image.open(BytesIO(raw))
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.load()
    return image


def _save_page(image: Image.Image, project_id: int, index: int) -> tuple[str, int, int]:
    filename = f"p_{index:04d}.jpg"
    page_file = paths.page_path(project_id, filename)
    image.save(page_file, "JPEG", quality=88)
    thumb = image.copy()
    thumb.thumbnail((480, 480))
    thumb.save(paths.thumb_path(project_id, filename), "JPEG", quality=70)
    width, height = image.size
    return filename, width, height


def begin_import(title: str, filename: str) -> dict:
    """Fast skeleton rows. The slow page work happens in ingest_upload."""
    safe_name = Path(filename).name
    project_id = project_queries.create_project(title)
    chapter_id = project_queries.create_chapter(project_id, title, safe_name)
    job_id = job_queries.create_job(project_id, "import")
    paths.ensure_project_dirs(project_id)
    return {"project_id": project_id, "chapter_id": chapter_id, "job_id": job_id}


def _wipe_chapter_pages(project_id: int, chapter_id: int) -> None:
    for page in page_queries.list_pages(chapter_id):
        for variant in ("pages", "thumbs"):
            target = paths.safe_join(
                "projects", str(project_id), variant, str(page["filename"])
            )
            target.unlink(missing_ok=True)
    page_queries.delete_pages_by_chapter(chapter_id)
    project_queries.set_page_count(chapter_id, 0)


def ingest_upload(
    tmp_path: str,
    filename: str,
    title: str,
    *,
    ids: dict | None = None,
    progress: Callable[[int, int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> dict:
    report = progress or (lambda _done, _total: None)
    stop = should_stop or (lambda: False)
    if ids is None:
        owned = begin_import(title, filename)
        project_id = owned["project_id"]
        chapter_id = owned["chapter_id"]
        job_id = owned["job_id"]
    else:
        project_id = ids["project_id"]
        chapter_id = ids["chapter_id"]
        job_id = ids["job_id"]
        _wipe_chapter_pages(project_id, chapter_id)
    job_queries.update_job(job_id, status="running", progress=5)
    try:
        size_mb = Path(tmp_path).stat().st_size / (1024 * 1024)
        if size_mb > config.max_upload_mb():
            raise ValueError(f"file too large ({size_mb:.0f} MB)")
        if not zipfile.is_zipfile(tmp_path):
            raise ValueError("not a CBZ or ZIP archive")
        safe_name = Path(filename).name
        shutil.copy(
            tmp_path,
            paths.safe_join("projects", str(project_id), "originals", safe_name),
        )
        skipped = 0
        rows: list[dict] = []
        with zipfile.ZipFile(tmp_path) as archive:
            members = [
                info.filename for info in archive.infolist() if not info.is_dir()
            ]
            usable = sorted(
                [name for name in members if _is_usable_member(name)],
                key=lambda name: natural_key(name.rsplit("/", 1)[-1]),
            )
            skipped = len(members) - len(usable)
            total = len(usable)
            saved = 0
            for position, name in enumerate(usable, start=1):
                if stop():
                    raise JobCancelled()
                try:
                    image = _normalize_image(archive.read(name))
                except Exception as exc:
                    skipped += 1
                    logger.warning("[ingest] skip corrupt image %s (%s)", name, exc)
                    continue
                saved += 1
                saved_file, width, height = _save_page(image, project_id, saved)
                rows.append(
                    {
                        "page_index": saved,
                        "page_id": f"ch{chapter_id}_p{saved:04d}",
                        "filename": saved_file,
                        "rel_path": f"projects/{project_id}/pages/{saved_file}",
                        "width": width,
                        "height": height,
                    }
                )
                report(position, total)
        if not rows:
            raise ValueError("no readable image found in archive")
        page_queries.bulk_insert_pages(chapter_id, rows)
        project_queries.set_page_count(chapter_id, len(rows))
        job_queries.update_job(job_id, status="done", progress=100)
        logger.info(
            "[ingest] project=%s chapter=%s pages=%s skipped=%s",
            project_id,
            chapter_id,
            len(rows),
            skipped,
        )
        return {
            "project_id": project_id,
            "chapter_id": chapter_id,
            "page_count": len(rows),
            "skipped": skipped,
            "job_id": job_id,
        }
    except JobCancelled:
        # Keep project, chapter and originals so retry works. No half pages.
        _wipe_chapter_pages(project_id, chapter_id)
        raise
    except Exception as exc:
        job_queries.update_job(job_id, status="failed", error=str(exc)[:300])
        logger.error("[ingest] project=%s failed: %s", project_id, exc)
        _wipe_chapter_pages(project_id, chapter_id)
        raise
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def retry_import(project_id: int) -> dict:
    """Replay a chapter from its kept originals. Returns new job ids."""
    chapters = project_queries.list_chapters(project_id)
    if not chapters:
        raise ValueError("project has no chapter")
    chapter = chapters[0]
    original = paths.safe_join(
        "projects", str(project_id), "originals", str(chapter["source_filename"])
    )
    if not original.exists():
        raise ValueError("original archive is gone, upload again")
    job_id = job_queries.create_job(project_id, "import")
    replay = paths.safe_join("tmp", f"retry_{uuid.uuid4().hex}.cbz")
    replay.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(original, replay)
    ids = {
        "project_id": project_id,
        "chapter_id": chapter["id"],
        "job_id": job_id,
    }
    return {"ids": ids, "tmp": str(replay), "title": chapter["title"]}
