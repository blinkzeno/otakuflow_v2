"""Project and chapter queries. No SQL lives outside this package."""

from sqlalchemy import text

from backend.db.database import session_scope


def create_project(title: str) -> int:
    with session_scope() as session:
        result = session.execute(
            text("INSERT INTO projects (title) VALUES (:title)"), {"title": title}
        )
        assert result.lastrowid is not None
        return int(result.lastrowid)


def get_project(project_id: int) -> dict | None:
    with session_scope() as session:
        row = session.execute(
            text("SELECT * FROM projects WHERE id = :id"), {"id": project_id}
        ).mappings().first()
        return dict(row) if row else None


def list_projects() -> list[dict]:
    with session_scope() as session:
        rows = session.execute(
            text("SELECT * FROM projects ORDER BY id DESC")
        ).mappings().all()
        return [dict(row) for row in rows]


def delete_project(project_id: int) -> None:
    with session_scope() as session:
        session.execute(
            text("DELETE FROM projects WHERE id = :id"), {"id": project_id}
        )


def create_chapter(project_id: int, title: str, source_filename: str) -> int:
    with session_scope() as session:
        result = session.execute(
            text(
                "INSERT INTO chapters (project_id, title, source_filename)"
                " VALUES (:project_id, :title, :source_filename)"
            ),
            {
                "project_id": project_id,
                "title": title,
                "source_filename": source_filename,
            },
        )
        assert result.lastrowid is not None
        return int(result.lastrowid)


def set_page_count(chapter_id: int, page_count: int) -> None:
    with session_scope() as session:
        session.execute(
            text("UPDATE chapters SET page_count = :n WHERE id = :id"),
            {"n": page_count, "id": chapter_id},
        )


def get_chapter(chapter_id: int) -> dict | None:
    with session_scope() as session:
        row = session.execute(
            text("SELECT * FROM chapters WHERE id = :id"), {"id": chapter_id}
        ).mappings().first()
        return dict(row) if row else None


def list_chapters(project_id: int) -> list[dict]:
    with session_scope() as session:
        rows = session.execute(
            text(
                "SELECT * FROM chapters WHERE project_id = :project_id"
                " ORDER BY id ASC"
            ),
            {"project_id": project_id},
        ).mappings().all()
        return [dict(row) for row in rows]


def update_chapter_summary(chapter_id: int, summary_json: str) -> None:
    with session_scope() as session:
        session.execute(
            text("UPDATE chapters SET chapter_summary = :summary WHERE id = :id"),
            {"summary": summary_json, "id": chapter_id},
        )
