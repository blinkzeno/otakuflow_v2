"""Jobs infra: background progress, mid run cancel, AI pacing."""

import time

from backend.db.queries import jobs as job_queries
from backend.db.queries import projects as project_queries
from backend.services import jobs


def _make_project(fresh_db):
    _ = fresh_db
    return project_queries.create_project("Jobs")


def _runner(total, progress, should_stop):
    for done in range(1, total + 1):
        if should_stop():
            raise jobs.JobCancelled()
        time.sleep(0.005)
        progress(done, total)


def test_background_job_reports_done(tmp_path, fresh_db):
    project_id = _make_project(fresh_db)
    job_id = job_queries.create_job(project_id, "import")
    future = jobs.enqueue(project_id, job_id, _runner, 10)
    future.result(timeout=15)
    job = job_queries.get_job(job_id)
    assert job["status"] == "done"
    assert job["progress"] == 100
    assert len(jobs.read_log_tail(job_id)) >= 2


def test_cancel_mid_run(tmp_path, fresh_db):
    project_id = _make_project(fresh_db)
    job_id = job_queries.create_job(project_id, "import")
    future = jobs.enqueue(project_id, job_id, _runner, 200)
    for _ in range(100):
        if (job_queries.get_job(job_id) or {}).get("progress", 0) > 0:
            break
        time.sleep(0.02)
    jobs.request_cancel(job_id)
    future.result(timeout=15)
    assert job_queries.get_job(job_id)["status"] == "cancelled"


def test_interrupted_jobs_marked_failed(tmp_path, fresh_db):
    project_id = _make_project(fresh_db)
    job_id = job_queries.create_job(project_id, "import")
    job_queries.update_job(job_id, status="running")
    assert jobs.mark_interrupted_jobs() == 1
    job = job_queries.get_job(job_id)
    assert job["status"] == "failed"
    assert "restart" in (job["error"] or "")


def test_ai_gate_spaces_calls(tmp_path, fresh_db, monkeypatch):
    _ = fresh_db
    monkeypatch.setenv("VISION_MIN_INTERVAL_SEC", "0.3")
    jobs._last_ai_call.clear()
    start = time.monotonic()
    jobs.ai_gate("probe")
    jobs.ai_gate("probe")
    assert time.monotonic() - start >= 0.3
