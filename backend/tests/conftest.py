"""Shared fixture: isolated database per test."""

import pytest

from backend.db import database


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    database._engine = None
    database._SessionLocal = None
    return database.init_db()
