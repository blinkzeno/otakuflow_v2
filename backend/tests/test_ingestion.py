"""Ingestion test: trap names sort right, junk is skipped, originals kept."""

import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image, ImageStat

from backend.db.queries import jobs as job_queries
from backend.db.queries import pages as page_queries
from backend.db.queries import projects as project_queries
from backend.services import ingestion
from backend.services.jobs import JobCancelled
from backend.storage import paths


def _jpeg_bytes(color: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (100, 150), color).save(buffer, "JPEG")
    return buffer.getvalue()


def test_ingest_traps_and_skips(tmp_path, fresh_db):
    _ = fresh_db
    archive = tmp_path / "trap.cbz"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("page_10.jpg", _jpeg_bytes("red"))
        bundle.writestr("page_2.jpg", _jpeg_bytes("green"))
        bundle.writestr("page_1.jpg", _jpeg_bytes("blue"))
        bundle.writestr("notes.txt", b"ignore me")
        bundle.writestr("__MACOSX/._page_1.jpg", b"junk")
        bundle.writestr("broken.png", b"not an image at all")
    result = ingestion.ingest_upload(str(archive), "trap.cbz", "Trap Ch.1")
    assert result["page_count"] == 3
    assert result["skipped"] == 3
    chapter_id = result["chapter_id"]
    stored = page_queries.list_pages(chapter_id)
    assert [page["page_index"] for page in stored] == [1, 2, 3]
    assert [page["page_id"] for page in stored] == [
        f"ch{chapter_id}_p0001",
        f"ch{chapter_id}_p0002",
        f"ch{chapter_id}_p0003",
    ]
    project_id = result["project_id"]
    assert paths.safe_join(
        "projects", str(project_id), "originals", "trap.cbz"
    ).exists()
    for position in (1, 2, 3):
        assert paths.page_path(project_id, f"p_{position:04d}.jpg").exists()
        assert paths.thumb_path(project_id, f"p_{position:04d}.jpg").exists()
    # Content order, not just numbering: page_1 (blue) first, page_10 (red) last.
    project_root = Path(paths.project_dir(project_id))
    dominant = []
    for position in (1, 2, 3):
        bands = ImageStat.Stat(
            Image.open(project_root / "pages" / f"p_{position:04d}.jpg")
        ).mean
        dominant.append("rgb"[bands.index(max(bands))])
    assert dominant == ["b", "g", "r"]


def test_ingest_rejects_non_archive(tmp_path, fresh_db):
    _ = fresh_db
    fake = tmp_path / "evil.cbz"
    fake.write_bytes(b"MZ binary, not a zip")
    try:
        ingestion.ingest_upload(str(fake), "evil.cbz", "Evil")
        raise AssertionError("should have raised")
    except ValueError as exc:
        assert "not a CBZ" in str(exc)
    # Project row stays (retryable) but holds zero pages.
    projects = project_queries.list_projects()
    assert len(projects) == 1
    chapters = project_queries.list_chapters(projects[0]["id"])
    assert chapters[0]["page_count"] == 0
    assert page_queries.list_pages(chapters[0]["id"]) == []


def _two_page_cbz(path):
    with zipfile.ZipFile(path, "w") as bundle:
        for name, color in (("page_2.jpg", "green"), ("page_1.jpg", "blue")):
            buffer = BytesIO()
            Image.new("RGB", (60, 90), color).save(buffer, "JPEG")
            bundle.writestr(name, buffer.getvalue())


def test_cancel_keeps_originals_then_retry_completes(tmp_path, fresh_db):
    _ = fresh_db
    archive = tmp_path / "ch1src.cbz"
    _two_page_cbz(archive)
    with pytest.raises(JobCancelled):
        ingestion.ingest_upload(
            str(archive), "ch1.cbz", "Ch.1", should_stop=lambda: True
        )
    project = project_queries.list_projects()[0]
    chapter = project_queries.list_chapters(project["id"])[0]
    assert chapter["page_count"] == 0
    assert paths.safe_join(
        "projects", str(project["id"]), "originals", "ch1.cbz"
    ).exists()
    replay = ingestion.retry_import(project["id"])
    done = ingestion.ingest_upload(
        replay["tmp"],
        "ch1.cbz",
        replay["title"],
        ids=replay["ids"],
    )
    assert done["page_count"] == 2
    assert project_queries.get_chapter(chapter["id"])["page_count"] == 2
    job = job_queries.get_job(replay["ids"]["job_id"])
    assert job["status"] == "done"
