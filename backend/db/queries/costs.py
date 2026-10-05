"""Quota ledger. cost_usd stays 0 on free tiers, calls are counted."""

from sqlalchemy import text

from backend.db.database import session_scope


def log_call(
    chapter_id: int, provider: str, model: str, kind: str, units: dict
) -> None:
    import json

    with session_scope() as session:
        session.execute(
            text(
                "INSERT INTO ai_costs (chapter_id, provider, model, kind, units_json)"
                " VALUES (:chapter_id, :provider, :model, :kind, :units)"
            ),
            {
                "chapter_id": chapter_id,
                "provider": provider,
                "model": model,
                "kind": kind,
                "units": json.dumps(units),
            },
        )


def calls_today(provider: str) -> int:
    with session_scope() as session:
        row = session.execute(
            text(
                "SELECT COUNT(*) AS n FROM ai_costs"
                " WHERE provider = :provider"
                " AND date(created_at) = date('now')"
            ),
            {"provider": provider},
        ).mappings().first()
        assert row is not None
        return int(row["n"])


def calls_today_for_model(model: str) -> int:
    with session_scope() as session:
        row = session.execute(
            text(
                "SELECT COUNT(*) AS n FROM ai_costs"
                " WHERE model = :model"
                " AND date(created_at) = date('now')"
            ),
            {"model": model},
        ).mappings().first()
        assert row is not None
        return int(row["n"])
