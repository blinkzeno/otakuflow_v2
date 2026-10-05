"""Render bookkeeping: one row per attempt, latest wins for playback."""

import json

from sqlalchemy import text

from backend.db.database import session_scope


def create_render(chapter_id: int, settings: dict) -> int:
    with session_scope() as session:
        result = session.execute(
            text(
                "INSERT INTO renders (chapter_id, timeline_json, settings_json)"
                " VALUES (:chapter_id, '[]', :settings)"
            ),
            {"chapter_id": chapter_id, "settings": json.dumps(settings)},
        )
        assert result.lastrowid is not None
        return int(result.lastrowid)


def complete_render(
    render_id: int, timeline_json: str, video_rel: str | None, status: str
) -> None:
    with session_scope() as session:
        session.execute(
            text(
                "UPDATE renders SET timeline_json = :timeline,"
                " video_rel_path = :video, status = :status WHERE id = :id"
            ),
            {
                "timeline": timeline_json,
                "video": video_rel,
                "status": status,
                "id": render_id,
            },
        )


def get_render(render_id: int) -> dict | None:
    with session_scope() as session:
        row = session.execute(
            text("SELECT * FROM renders WHERE id = :id"), {"id": render_id}
        ).mappings().first()
        return dict(row) if row else None


def latest_render(chapter_id: int) -> dict | None:
    with session_scope() as session:
        row = session.execute(
            text(
                "SELECT * FROM renders WHERE chapter_id = :chapter_id"
                " AND status = 'done' ORDER BY id DESC LIMIT 1"
            ),
            {"chapter_id": chapter_id},
        ).mappings().first()
        return dict(row) if row else None
