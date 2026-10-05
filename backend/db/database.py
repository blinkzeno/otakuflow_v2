"""SQLite engine (WAL) plus session helpers.

One session per unit of work, never shared across threads.
Schema truth lives in schema.sql, applied here with executescript.
"""

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from backend.core import config

logger = logging.getLogger("otakuflow")

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
SCHEMA_VERSION = 1

_engine = None
_SessionLocal = None


def db_path() -> Path:
    return config.data_root() / "otakuflow.db"


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(
            f"sqlite:///{db_path()}",
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(_engine, "connect")
        def _set_wal(dbapi_conn, _record):
            dbapi_conn.execute("PRAGMA journal_mode=WAL")

        _SessionLocal = sessionmaker(bind=_engine)
    return _engine


@contextmanager
def session_scope() -> Iterator[Session]:
    get_engine()
    assert _SessionLocal is not None
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> Path:
    """Create DATA_DIR and the database file if missing. Idempotent."""
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = sqlite3.connect(path)
    try:
        conn.executescript(sql)
        conn.execute("PRAGMA journal_mode=WAL")
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,)
            )
        conn.commit()
    finally:
        conn.close()
    get_engine()
    logger.info("[db] init ok path=%s", path)
    return path
