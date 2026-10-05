"""Page queries. Pages are always read in reading order."""

from sqlalchemy import text

from backend.db.database import session_scope


def bulk_insert_pages(chapter_id: int, rows: list[dict]) -> None:
    """Insert many pages in one transaction. Raises on duplicate page_id."""
    with session_scope() as session:
        session.execute(
            text(
                "INSERT INTO pages (chapter_id, page_index, page_id, filename,"
                " rel_path, width, height)"
                " VALUES (:chapter_id, :page_index, :page_id, :filename,"
                " :rel_path, :width, :height)"
            ),
            [{**row, "chapter_id": chapter_id} for row in rows],
        )


def list_pages(chapter_id: int) -> list[dict]:
    with session_scope() as session:
        rows = session.execute(
            text(
                "SELECT * FROM pages WHERE chapter_id = :chapter_id"
                " ORDER BY page_index ASC"
            ),
            {"chapter_id": chapter_id},
        ).mappings().all()
        return [dict(row) for row in rows]


def get_page(page_id: int) -> dict | None:
    with session_scope() as session:
        row = session.execute(
            text("SELECT * FROM pages WHERE id = :id"), {"id": page_id}
        ).mappings().first()
        return dict(row) if row else None


def delete_pages_by_chapter(chapter_id: int) -> None:
    with session_scope() as session:
        session.execute(
            text("DELETE FROM pages WHERE chapter_id = :chapter_id"),
            {"chapter_id": chapter_id},
        )


def pending_pages(chapter_id: int) -> list[dict]:
    with session_scope() as session:
        rows = session.execute(
            text(
                "SELECT * FROM pages WHERE chapter_id = :chapter_id"
                " AND analysis_status != 'done'"
                " ORDER BY page_index ASC"
            ),
            {"chapter_id": chapter_id},
        ).mappings().all()
        return [dict(row) for row in rows]


def update_analysis(
    page_id: int,
    analysis_json: str | None = None,
    importance: int | None = None,
    status: str = "done",
    error: str | None = None,
) -> None:
    with session_scope() as session:
        session.execute(
            text(
                "UPDATE pages SET analysis_json = :json, importance = :importance,"
                " analysis_status = :status, analysis_error = :error"
                " WHERE id = :id"
            ),
            {
                "json": analysis_json,
                "importance": importance,
                "status": status,
                "error": error,
                "id": page_id,
            },
        )
