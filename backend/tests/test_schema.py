"""Schema test: tables exist, WAL is on, queries round trip."""

import sqlite3

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.db import database
from backend.db.queries import jobs as job_queries
from backend.db.queries import pages as page_queries
from backend.db.queries import projects as project_queries

EXPECTED_TABLES = {
    "schema_version",
    "projects",
    "chapters",
    "pages",
    "script_segments",
    "audio_segments",
    "renders",
    "jobs",
    "ai_costs",
}


def _fresh_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    database._engine = None
    database._SessionLocal = None
    return database.init_db()


def test_tables_exist_and_wal_on(tmp_path, monkeypatch):
    path = _fresh_db(tmp_path, monkeypatch)
    assert path.exists()
    conn = sqlite3.connect(path)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert EXPECTED_TABLES <= tables
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        version = conn.execute("SELECT version FROM schema_version").fetchone()
        assert version is not None and version[0] == 1
    finally:
        conn.close()


def test_init_is_idempotent(tmp_path, monkeypatch):
    first = _fresh_db(tmp_path, monkeypatch)
    second = database.init_db()
    assert first == second


def test_startup_creates_database(tmp_path, monkeypatch):
    """Guards the wiring: app startup must run init_db (lifespan attached)."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    database._engine = None
    database._SessionLocal = None
    with TestClient(app):
        pass
    assert (tmp_path / "data" / "otakuflow.db").exists()


def test_project_chapter_pages_roundtrip(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    project_id = project_queries.create_project("Ch.1")
    chapter_id = project_queries.create_chapter(project_id, "Ch.1", "ch1.cbz")
    page_queries.bulk_insert_pages(
        chapter_id,
        [
            {
                "page_index": 2,
                "page_id": f"ch{chapter_id}_p0002",
                "filename": "p_0002.jpg",
                "rel_path": "projects/1/pages/p_0002.jpg",
                "width": 800,
                "height": 1200,
            },
            {
                "page_index": 1,
                "page_id": f"ch{chapter_id}_p0001",
                "filename": "p_0001.jpg",
                "rel_path": "projects/1/pages/p_0001.jpg",
                "width": 800,
                "height": 1200,
            },
        ],
    )
    project_queries.set_page_count(chapter_id, 2)
    pages = page_queries.list_pages(chapter_id)
    assert [page["page_index"] for page in pages] == [1, 2]
    job_id = job_queries.create_job(project_id, "import")
    job_queries.update_job(job_id, status="done", progress=100)
    assert job_queries.get_job(job_id)["status"] == "done"
    assert len(job_queries.list_jobs(project_id)) == 1
