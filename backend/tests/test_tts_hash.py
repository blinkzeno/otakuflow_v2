"""Voice hash logic with fake synth and fake durations, no network."""

from backend.db.queries import audio as audio_queries
from backend.db.queries import projects as project_queries
from backend.db.queries import segments as segment_queries
from backend.services import tts


def _chapter_with_reviewed(tmp_path, fresh_db, monkeypatch):
    _ = (tmp_path, fresh_db)
    monkeypatch.setattr(
        tts,
        "synthesize_fn",
        lambda _text, _voice: b"FAKEAUDIO",
    )
    monkeypatch.setattr(tts, "duration_fn", lambda _path: 12.5)
    project_id = project_queries.create_project("Voice")
    chapter_id = project_queries.create_chapter(project_id, "Voice", "v.cbz")
    segment_queries.insert_many(
        chapter_id,
        [
            {
                "position": 1,
                "segment_key": f"ch{chapter_id}_s001",
                "text": "Hello world.",
                "page_refs": "[]",
                "duration_estimate": 1.0,
                "status": "reviewed",
            }
        ],
    )
    return chapter_id


def test_first_run_synthesizes(tmp_path, fresh_db, monkeypatch):
    chapter_id = _chapter_with_reviewed(tmp_path, fresh_db, monkeypatch)
    result = tts.ensure_voices(chapter_id)
    assert result == {"voiced": 1, "skipped": 0, "failed": 0}
    segment = segment_queries.list_ordered(chapter_id)[0]
    assert segment["status"] == "voiced"
    audio = audio_queries.get_by_segment(segment["id"])
    assert audio is not None
    assert audio["duration"] == 12.5
    assert audio["text_hash"] == tts.text_hash("Hello world.")


def test_unchanged_text_skips_network(tmp_path, fresh_db, monkeypatch):
    chapter_id = _chapter_with_reviewed(tmp_path, fresh_db, monkeypatch)
    tts.ensure_voices(chapter_id)
    calls = {"n": 0}

    def counting(_text, _voice):
        calls["n"] += 1
        return b"FAKEAUDIO"

    monkeypatch.setattr(tts, "synthesize_fn", counting)
    result = tts.ensure_voices(chapter_id)
    assert result == {"voiced": 0, "skipped": 1, "failed": 0}
    assert calls["n"] == 0


def test_changed_text_regenerates_only_it(tmp_path, fresh_db, monkeypatch):
    chapter_id = _chapter_with_reviewed(tmp_path, fresh_db, monkeypatch)
    tts.ensure_voices(chapter_id)
    segment = segment_queries.list_ordered(chapter_id)[0]
    segment_queries.update_segment(segment["id"], text="Hello changed world.")
    calls = {"n": 0}

    def counting(_text, _voice):
        calls["n"] += 1
        return b"FAKEAUDIO"

    monkeypatch.setattr(tts, "synthesize_fn", counting)
    result = tts.ensure_voices(chapter_id)
    assert result == {"voiced": 1, "skipped": 0, "failed": 0}
    assert calls["n"] == 1
    out = tts.regenerate_one(segment["segment_key"])
    assert out == {"duration": 12.5}
    assert calls["n"] == 2
    refreshed = segment_queries.list_ordered(chapter_id)[0]
    assert refreshed["status"] == "voiced"


def test_bad_duration_counts_failed(tmp_path, fresh_db, monkeypatch):
    chapter_id = _chapter_with_reviewed(tmp_path, fresh_db, monkeypatch)
    monkeypatch.setattr(tts, "duration_fn", lambda _path: 0.0)
    result = tts.ensure_voices(chapter_id)
    assert result == {"voiced": 0, "skipped": 0, "failed": 1}
    segment = segment_queries.list_ordered(chapter_id)[0]
    assert segment["status"] == "reviewed"
    assert audio_queries.get_by_segment(segment["id"]) is None


def test_draft_gate_refuses_bulk(tmp_path, fresh_db, monkeypatch):
    chapter_id = _chapter_with_reviewed(tmp_path, fresh_db, monkeypatch)
    segment = segment_queries.list_ordered(chapter_id)[0]
    segment_queries.update_segment(segment["id"], status="draft")
    try:
        tts.ensure_voices(chapter_id)
        raise AssertionError("should have raised")
    except ValueError as exc:
        assert "review" in str(exc)
