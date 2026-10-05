"""Security smoke: rejections are clean, secrets never leak."""

import time
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from backend.api.main import app
from backend.db.queries import jobs as job_queries
from backend.db.queries import pages as page_queries
from backend.db.queries import projects as project_queries
from backend.storage import paths

client = TestClient(app)
ROOT = Path(__file__).resolve().parent.parent.parent


def test_upload_wrong_extension_rejected(tmp_path, fresh_db):
    _ = (tmp_path, fresh_db)
    response = client.post(
        "/api/projects",
        files={"file": ("evil.exe", b"MZ binary", "application/octet-stream")},
        data={"title": "Evil"},
    )
    assert response.status_code == 422
    assert "AIza" not in response.text


def test_upload_fake_archive_rejected(tmp_path, fresh_db):
    _ = fresh_db
    response = client.post(
        "/api/projects",
        files={"file": ("fake.cbz", b"not a zip", "application/zip")},
        data={"title": "Fake"},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        job = job_queries.get_job(job_id)
        assert job is not None
        if job["status"] in ("done", "failed", "cancelled", "paused"):
            break
        time.sleep(0.5)
    job = job_queries.get_job(job_id)
    assert job is not None
    assert job["status"] == "failed"
    assert "not a CBZ" in (job["error"] or "")
    assert "Traceback" not in (job["error"] or "")


def test_unknown_ids_404(tmp_path, fresh_db):
    _ = fresh_db
    assert client.get("/api/pages/999999").status_code == 404
    assert client.get("/api/pages/999999/image").status_code == 404
    assert client.get("/api/projects/999999").status_code == 404
    assert client.get("/api/renders/999999/video").status_code == 404


def test_analyze_without_key_fails_clean(tmp_path, fresh_db, monkeypatch):
    _ = fresh_db
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    project_id = project_queries.create_project("NoKey")
    chapter_id = project_queries.create_chapter(project_id, "NoKey", "n.cbz")
    paths.ensure_project_dirs(project_id)
    target = paths.page_path(project_id, "p_0001.jpg")
    Image.new("RGB", (60, 90), "white").save(target, "JPEG")
    page_queries.bulk_insert_pages(
        chapter_id,
        [
            {
                "page_index": 1,
                "page_id": f"ch{chapter_id}_p0001",
                "filename": "p_0001.jpg",
                "rel_path": f"projects/{project_id}/pages/p_0001.jpg",
                "width": 60,
                "height": 90,
            }
        ],
    )
    response = client.post(f"/api/chapters/{chapter_id}/analyze")
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        job = job_queries.get_job(job_id)
        assert job is not None
        if job["status"] in ("done", "failed", "cancelled", "paused"):
            break
        time.sleep(0.5)
    job = job_queries.get_job(job_id)
    assert job is not None
    assert job["status"] in ("done", "failed")
    page = page_queries.list_pages(chapter_id)[0]
    assert page["analysis_status"] == "failed"
    assert "GEMINI_API_KEY" in (page["analysis_error"] or "")
    assert "AIza" not in (page["analysis_error"] or "")


def test_env_file_is_ignored():
    import subprocess

    lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in lines
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", ".env"],
        cwd=ROOT,
        capture_output=True,
        timeout=30,
    )
    assert ignored.returncode == 0
