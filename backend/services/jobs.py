"""Background workers with progress, cooperative cancel and AI pacing.

Every long stage runs through enqueue. Runners receive two callbacks:
progress(done, total) and should_stop() which raise JobCancelled when the
user cancels. AI calls go through ai_gate plus ai_backoff so free quotas
are respected. Quota exhaustion raises QuotaPaused, never loops forever.
"""

import logging
import threading
import time
from collections import defaultdict
from concurrent.futures import Future, ThreadPoolExecutor

from backend.core import config
from backend.db.queries import jobs as job_queries
from backend.storage import paths

logger = logging.getLogger("otakuflow")


class JobCancelled(Exception):
    """Raised inside a runner when the user cancels. Never retried."""


class QuotaPaused(Exception):
    """Raised after repeated 429s. The job pauses for a later resume."""


_executor: ThreadPoolExecutor | None = None
_cancel_flags: dict[int, threading.Event] = {}
_project_locks: dict = defaultdict(threading.Lock)
_log_lock = threading.Lock()
_gate_lock = threading.Lock()
_last_ai_call: dict[str, float] = {}


def _executor_instance() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(
            max_workers=config.job_workers(), thread_name_prefix="otakuflow"
        )
    return _executor


def should_stop(job_id: int) -> bool:
    flag = _cancel_flags.get(job_id)
    return flag.is_set() if flag is not None else False


def request_cancel(job_id: int) -> bool:
    flag = _cancel_flags.get(job_id)
    if flag is None:
        return False
    flag.set()
    return True


def report_progress(job_id: int, done: int, total: int) -> None:
    total = max(total, 1)
    pct = max(0, min(100, int(100 * done / total)))
    job_queries.update_job(job_id, progress=pct)


def append_log(job_id: int, line: str) -> None:
    job = job_queries.get_job(job_id)
    if job is None or not job.get("log_path"):
        return
    path = paths.safe_join(*str(job["log_path"]).split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with _log_lock:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"[{time.strftime('%H:%M:%S')}] {line}\n")


def read_log_tail(job_id: int, limit: int = 200) -> list[str]:
    job = job_queries.get_job(job_id)
    if job is None or not job.get("log_path"):
        return []
    path = paths.safe_join(*str(job["log_path"]).split("/"))
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    return lines[-limit:]


def ai_gate(provider: str) -> None:
    """Wait until MIN_INTERVAL seconds passed since the last call."""
    interval = config.min_interval()
    with _gate_lock:
        wait = interval - (time.monotonic() - _last_ai_call.get(provider, 0.0))
    if wait > 0:
        time.sleep(wait)
    with _gate_lock:
        _last_ai_call[provider] = time.monotonic()


def ai_backoff(attempt: int) -> None:
    time.sleep(min(2**attempt, 60))


def _run_job(job_id: int, project_id: int, fn, args, kwargs) -> None:
    lock = _project_locks[project_id]
    with lock:
        job_queries.update_job(job_id, status="running")
        append_log(job_id, "job started")
        try:
            fn(
                *args,
                progress=lambda done, total: report_progress(job_id, done, total),
                should_stop=lambda: should_stop(job_id),
                **kwargs,
            )
        except JobCancelled:
            job_queries.update_job(
                job_id, status="cancelled", error="cancelled by user"
            )
            append_log(job_id, "job cancelled")
            return
        except QuotaPaused as exc:
            job_queries.update_job(job_id, status="paused", error=str(exc)[:300])
            append_log(job_id, f"job paused: {exc}")
            return
        except Exception as exc:
            logger.error("[jobs] job=%s failed: %s", job_id, exc)
            job_queries.update_job(job_id, status="failed", error=str(exc)[:300])
            append_log(job_id, f"job failed: {exc}"[:300])
            return
        finally:
            _cancel_flags.pop(job_id, None)
        job = job_queries.get_job(job_id)
        if job is not None and job["status"] == "running":
            job_queries.update_job(job_id, status="done", progress=100)
        if (job_queries.get_job(job_id) or {}).get("status") == "done":
            append_log(job_id, "job done")


def enqueue(project_id: int, job_id: int, fn, *args, **kwargs) -> Future:
    _cancel_flags[job_id] = threading.Event()
    job_queries.update_job(
        job_id, log_path=f"projects/{project_id}/logs/job_{job_id}.log"
    )
    append_log(job_id, "job queued")
    return _executor_instance().submit(_run_job, job_id, project_id, fn, args, kwargs)


def mark_interrupted_jobs() -> int:
    """Jobs left running by a restart can never finish. Mark them failed."""
    count = 0
    for job in job_queries.list_active_jobs():
        job_queries.update_job(
            job["id"], status="failed", error="interrupted by restart, relaunch it"
        )
        count += 1
    if count:
        logger.warning("[jobs] marked %s interrupted jobs as failed", count)
    return count
