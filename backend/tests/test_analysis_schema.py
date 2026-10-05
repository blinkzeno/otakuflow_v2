"""Analysis validation plus service flow with a mocked provider."""

import json

from PIL import Image
from pydantic import ValidationError
import pytest

from backend.db.queries import costs as cost_queries
from backend.db.queries import pages as page_queries
from backend.db.queries import projects as project_queries
from backend.providers.base import PageAnalysis, ProviderError
from backend.services import analysis
from backend.services import jobs as job_service
from backend.storage import paths


def _valid_payload() -> dict:
    return {
        "characters": ["blonde swordsman"],
        "actions": ["raises his sword"],
        "dialogues": [{"speaker": "??", "text": "Come on!"}],
        "events": ["duel starts"],
        "location": "rooftop at night",
        "importance": 8,
        "summary": "A swordsman issues a challenge on a rooftop.",
        "visual_description": "Dark rooftop, speed lines, close framing.",
    }


def test_schema_accepts_valid_payload():
    parsed = PageAnalysis.model_validate(_valid_payload())
    assert parsed.importance == 8
    assert parsed.dialogues[0].text == "Come on!"


def test_schema_rejects_missing_summary():
    payload = _valid_payload()
    del payload["summary"]
    with pytest.raises(ValidationError):
        PageAnalysis.model_validate(payload)


def test_schema_rejects_bad_importance():
    payload = _valid_payload()
    payload["importance"] = 99
    with pytest.raises(ValidationError):
        PageAnalysis.model_validate(payload)


def _payload_with_index(position: int) -> PageAnalysis:
    data = _valid_payload()
    data["batch_index"] = position
    return PageAnalysis.model_validate(data)


def _chapter_with_image(tmp_path, fresh_db, monkeypatch, color=(10, 10, 10)):
    return _chapter_with_pages(tmp_path, fresh_db, monkeypatch, 1, color)


def _chapter_with_pages(tmp_path, fresh_db, monkeypatch, count, color=(10, 10, 10)):
    _ = (tmp_path, fresh_db)
    monkeypatch.setattr(job_service, "ai_gate", lambda _provider: None)
    monkeypatch.setattr(job_service, "ai_backoff", lambda _attempt: None)
    project_id = project_queries.create_project("Vision")
    chapter_id = project_queries.create_chapter(project_id, "Vision", "v.cbz")
    paths.ensure_project_dirs(project_id)
    rows = []
    for position in range(1, count + 1):
        filename = f"p_{position:04d}.jpg"
        target = paths.page_path(project_id, filename)
        Image.new("RGB", (200, 300), color).save(target, "JPEG")
        rows.append(
            {
                "page_index": position,
                "page_id": f"ch{chapter_id}_p{position:04d}",
                "filename": filename,
                "rel_path": f"projects/{project_id}/pages/{filename}",
                "width": 200,
                "height": 300,
            }
        )
    page_queries.bulk_insert_pages(chapter_id, rows)
    return chapter_id


def test_service_writes_done_and_counts_quota(tmp_path, fresh_db, monkeypatch):
    from backend.providers import gemini_vision

    chapter_id = _chapter_with_image(tmp_path, fresh_db, monkeypatch)
    seen: dict = {}

    def fake(images, prompt, model):
        seen["images"] = len(images)
        seen["model"] = model
        return [_payload_with_index(1)], []

    monkeypatch.setattr(gemini_vision, "analyze_pages", fake)
    monkeypatch.setenv("VISION_MODEL", "test-vision")
    result = analysis.analyze_chapter(chapter_id)
    assert result == {"done": 1, "failed": 0}
    assert seen == {"images": 1, "model": "test-vision"}
    stored = page_queries.list_pages(chapter_id)[0]
    assert stored["analysis_status"] == "done"
    assert stored["importance"] == 8
    assert json.loads(stored["analysis_json"])["summary"].startswith("A swordsman")
    from backend.core import config as config_module

    assert cost_queries.calls_today_for_model(config_module.vision_model()) == 1


def test_service_marks_failed_but_continues(tmp_path, fresh_db, monkeypatch):
    from backend.providers import gemini_vision

    chapter_id = _chapter_with_image(tmp_path, fresh_db, monkeypatch)

    def boom(_images, _prompt, _model):
        raise ProviderError("invalid", "bad json forever")

    monkeypatch.setattr(gemini_vision, "analyze_pages", boom)
    result = analysis.analyze_chapter(chapter_id)
    assert result == {"done": 0, "failed": 1}
    stored = page_queries.list_pages(chapter_id)[0]
    assert stored["analysis_status"] == "failed"
    assert stored["analysis_error"]


def test_service_retries_transient_network_then_succeeds(
    tmp_path, fresh_db, monkeypatch
):
    from backend.providers import gemini_vision

    chapter_id = _chapter_with_image(tmp_path, fresh_db, monkeypatch)
    calls = {"n": 0}

    def flaky(_images, _prompt, _model):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ProviderError("network", "503 overloaded")
        return [_payload_with_index(1)], []

    monkeypatch.setattr(gemini_vision, "analyze_pages", flaky)
    result = analysis.analyze_chapter(chapter_id)
    assert result == {"done": 1, "failed": 0}
    assert calls["n"] == 2


def test_clamp_importance():
    assert analysis._clamp_importance(99) == 10
    assert analysis._clamp_importance(-3) == 0
    assert analysis._clamp_importance("x") == 0


def test_five_pages_split_into_two_plus_two_plus_one(tmp_path, fresh_db, monkeypatch):
    from backend.providers import gemini_vision

    chapter_id = _chapter_with_pages(tmp_path, fresh_db, monkeypatch, 5)
    monkeypatch.setenv("VISION_PAGES_PER_CALL", "2")
    monkeypatch.setenv("VISION_MODEL", "test-vision")
    sizes: list[int] = []

    def fake(images, prompt, model):
        sizes.append(len(images))
        assert model == "test-vision"
        return (
            [_payload_with_index(slot) for slot in range(1, len(images) + 1)],
            [],
        )

    monkeypatch.setattr(gemini_vision, "analyze_pages", fake)
    result = analysis.analyze_chapter(chapter_id)
    assert result == {"done": 5, "failed": 0}
    assert sizes == [2, 2, 1]
    stored = page_queries.list_pages(chapter_id)
    assert [page["analysis_status"] for page in stored] == ["done"] * 5


def test_quota_returns_two_buckets(tmp_path, fresh_db, monkeypatch):
    from fastapi.testclient import TestClient

    from backend.api.main import app

    _ = tmp_path
    monkeypatch.setenv("VISION_MODEL", "lite-m")
    monkeypatch.setenv("TEXT_MODEL", "strong-m")
    monkeypatch.setenv("VISION_DAILY_CAP", "500")
    monkeypatch.setenv("TEXT_DAILY_CAP", "20")
    body = TestClient(app).get("/api/quota").json()
    assert body == {
        "vision": {"model": "lite-m", "used": 0, "cap": 500},
        "text": {"model": "strong-m", "used": 0, "cap": 20},
    }


def test_bad_batch_index_isolates_page(tmp_path, fresh_db, monkeypatch):
    from backend.providers import gemini_vision

    chapter_id = _chapter_with_pages(tmp_path, fresh_db, monkeypatch, 3)
    monkeypatch.setenv("VISION_PAGES_PER_CALL", "8")

    def fake(images, prompt, model):
        good = [_payload_with_index(1), _payload_with_index(3)]
        liar = _valid_payload()
        liar["batch_index"] = 99
        good.append(PageAnalysis.model_validate(liar))
        return good, []

    monkeypatch.setattr(gemini_vision, "analyze_pages", fake)
    result = analysis.analyze_chapter(chapter_id)
    assert result == {"done": 2, "failed": 1}
    stored = page_queries.list_pages(chapter_id)
    assert [page["analysis_status"] for page in stored] == [
        "done",
        "failed",
        "done",
    ]
