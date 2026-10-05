"""Smoke test: the API answers on /api/health."""

from fastapi.testclient import TestClient

from backend.api.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
