"""Script segment queries. Positions stay dense 1..N after every op."""

from sqlalchemy import text

from backend.db.database import session_scope


def list_ordered(chapter_id: int) -> list[dict]:
    with session_scope() as session:
        rows = session.execute(
            text(
                "SELECT * FROM script_segments WHERE chapter_id = :chapter_id"
                " ORDER BY position ASC, id ASC"
            ),
            {"chapter_id": chapter_id},
        ).mappings().all()
        return [dict(row) for row in rows]


def get_by_key(segment_key: str) -> dict | None:
    with session_scope() as session:
        row = session.execute(
            text("SELECT * FROM script_segments WHERE segment_key = :key"),
            {"key": segment_key},
        ).mappings().first()
        return dict(row) if row else None


def insert_many(chapter_id: int, rows: list[dict]) -> None:
    with session_scope() as session:
        session.execute(
            text(
                "INSERT INTO script_segments (chapter_id, position, segment_key,"
                " text, page_refs, duration_estimate, status)"
                " VALUES (:chapter_id, :position, :segment_key,"
                " :text, :page_refs, :duration_estimate, :status)"
            ),
            [{**row, "chapter_id": chapter_id} for row in rows],
        )


def delete_by_status(chapter_id: int, status: str) -> int:
    with session_scope() as session:
        result = session.execute(
            text(
                "DELETE FROM script_segments"
                " WHERE chapter_id = :chapter_id AND status = :status"
            ),
            {"chapter_id": chapter_id, "status": status},
        )
        return result.rowcount or 0


def delete_all(chapter_id: int) -> None:
    with session_scope() as session:
        session.execute(
            text("DELETE FROM script_segments WHERE chapter_id = :chapter_id"),
            {"chapter_id": chapter_id},
        )


def update_segment(segment_id: int, **fields: object) -> None:
    allowed = {"text", "page_refs", "position", "status"}
    updates = {key: value for key, value in fields.items() if key in allowed}
    if not updates:
        return
    assignments = ", ".join(f"{key} = :{key}" for key in updates)
    with session_scope() as session:
        session.execute(
            text(f"UPDATE script_segments SET {assignments} WHERE id = :id"),
            {**updates, "id": segment_id},
        )


def update_key(segment_id: int, segment_key: str) -> None:
    with session_scope() as session:
        session.execute(
            text("UPDATE script_segments SET segment_key = :key WHERE id = :id"),
            {"key": segment_key, "id": segment_id},
        )


def delete_segment(segment_id: int) -> None:
    with session_scope() as session:
        session.execute(
            text("DELETE FROM script_segments WHERE id = :id"), {"id": segment_id}
        )


def mark_reviewed(chapter_id: int) -> int:
    with session_scope() as session:
        result = session.execute(
            text(
                "UPDATE script_segments SET status = 'reviewed'"
                " WHERE chapter_id = :chapter_id AND status = 'draft'"
            ),
            {"chapter_id": chapter_id},
        )
        return result.rowcount or 0


def has_draft(chapter_id: int) -> bool:
    with session_scope() as session:
        row = session.execute(
            text(
                "SELECT COUNT(*) AS n FROM script_segments"
                " WHERE chapter_id = :chapter_id AND status = 'draft'"
            ),
            {"chapter_id": chapter_id},
        ).mappings().first()
        assert row is not None
        return int(row["n"]) > 0
