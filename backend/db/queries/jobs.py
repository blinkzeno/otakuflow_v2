"""Job queries. Progress is written often, reads must stay cheap."""

from sqlalchemy import text

from backend.db.database import session_scope


def create_job(project_id: int, stage: str) -> int:
    with session_scope() as session:
        result = session.execute(
            text(
                "INSERT INTO jobs (project_id, stage) VALUES (:project_id, :stage)"
            ),
            {"project_id": project_id, "stage": stage},
        )
        assert result.lastrowid is not None
        return int(result.lastrowid)


def update_job(job_id: int, **fields: object) -> None:
    allowed = {"status", "progress", "log_path", "error"}
    updates = {key: value for key, value in fields.items() if key in allowed}
    if not updates:
        return
    assignments = ", ".join(f"{key} = :{key}" for key in updates)
    with session_scope() as session:
        session.execute(
            text(f"UPDATE jobs SET {assignments} WHERE id = :id"),
            {**updates, "id": job_id},
        )


def get_job(job_id: int) -> dict | None:
    with session_scope() as session:
        row = session.execute(
            text("SELECT * FROM jobs WHERE id = :id"), {"id": job_id}
        ).mappings().first()
        return dict(row) if row else None


def list_jobs(project_id: int) -> list[dict]:
    with session_scope() as session:
        rows = session.execute(
            text(
                "SELECT * FROM jobs WHERE project_id = :project_id"
                " ORDER BY id DESC"
            ),
            {"project_id": project_id},
        ).mappings().all()
        return [dict(row) for row in rows]


def list_active_jobs() -> list[dict]:
    with session_scope() as session:
        rows = session.execute(
            text(
                "SELECT * FROM jobs WHERE status IN ('queued', 'running')"
                " ORDER BY id ASC"
            )
        ).mappings().all()
        return [dict(row) for row in rows]
