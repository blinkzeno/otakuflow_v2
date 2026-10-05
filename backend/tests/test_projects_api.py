"""API regression: one upload creates exactly one project and finishes."""

import time
import zipfile
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from backend.api.main import app
from backend.db.queries import jobs as job_queries
from backend.db.queries import projects as project_queries

client = TestClient(app)


def _cbz_bytes() -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        for pos, name in enumerate(("page_2.jpg", "page_1.jpg")):
            img = BytesIO()
            Image.new("RGB", (60, 90), (10 + pos * 20,) * 3).save(img, "JPEG")
            bundle.writestr(name, img.getvalue())
    return buffer.getvalue()


def test_upload_creates_single_project_and_completes(tmp_path, fresh_db):
    _ = fresh_db
    response = client.post(
        "/api/projects",
        files={"file": ("one.cbz", _cbz_bytes(), "application/zip")},
        data={"title": "Single"},
    )
    assert response.status_code == 202
    body = response.json()
    assert [p["id"] for p in project_queries.list_projects()] == [
        body["project_id"]
    ]
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        job = job_queries.get_job(body["job_id"])
        assert job is not None
        if job["status"] == "done":
            break
        assert job["status"] not in ("failed", "cancelled")
        time.sleep(0.2)
    assert job_queries.get_job(body["job_id"])["status"] == "done"
    assert len(job_queries.list_jobs(body["project_id"])) == 1
