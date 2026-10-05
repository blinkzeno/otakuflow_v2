"""Audio bookkeeping: one row per segment, replaced on regen."""

from sqlalchemy import text

from backend.db.database import session_scope


def get_by_segment(segment_id: int) -> dict | None:
    with session_scope() as session:
        row = session.execute(
            text("SELECT * FROM audio_segments WHERE segment_id = :id"),
            {"id": segment_id},
        ).mappings().first()
        return dict(row) if row else None


def upsert_audio(segment_id: int, row: dict) -> None:
    with session_scope() as session:
        existing = session.execute(
            text("SELECT id FROM audio_segments WHERE segment_id = :id"),
            {"id": segment_id},
        ).first()
        if existing:
            session.execute(
                text(
                    "UPDATE audio_segments SET provider = :provider, voice = :voice,"
                    " rel_path = :rel_path, duration = :duration,"
                    " text_hash = :text_hash WHERE segment_id = :id"
                ),
                {**row, "id": segment_id},
            )
        else:
            session.execute(
                text(
                    "INSERT INTO audio_segments (segment_id, provider, voice,"
                    " rel_path, duration, text_hash)"
                    " VALUES (:segment_id, :provider, :voice,"
                    " :rel_path, :duration, :text_hash)"
                ),
                {"segment_id": segment_id, **row},
            )


def list_by_chapter(chapter_id: int) -> list[dict]:
    with session_scope() as session:
        rows = session.execute(
            text(
                "SELECT a.* FROM audio_segments a"
                " JOIN script_segments s ON s.id = a.segment_id"
                " WHERE s.chapter_id = :chapter_id"
            ),
            {"chapter_id": chapter_id},
        ).mappings().all()
        return [dict(row) for row in rows]
