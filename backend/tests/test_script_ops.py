"""Script ops: generate filtering, split, merge, reorder, review gate."""

import json

from backend.db.queries import pages as page_queries
from backend.db.queries import projects as project_queries
from backend.db.queries import segments as segment_queries
from backend.providers.base import ScriptDraft, SegmentDraft
from backend.services import script


def _chapter_with_pages(fresh_db):
    _ = fresh_db
    project_id = project_queries.create_project("Script")
    chapter_id = project_queries.create_chapter(project_id, "Script", "s.cbz")
    page_queries.bulk_insert_pages(
        chapter_id,
        [
            {
                "page_index": index,
                "page_id": f"ch{chapter_id}_p{index:04d}",
                "filename": f"p_{index:04d}.jpg",
                "rel_path": f"projects/{project_id}/pages/p_{index:04d}.jpg",
                "width": 100,
                "height": 150,
            }
            for index in range(1, 6)
        ],
    )
    for page in page_queries.list_pages(chapter_id):
        page_queries.update_analysis(
            page["id"], analysis_json='{"summary": "x"}', status="done"
        )
    return chapter_id


def _draft():
    return ScriptDraft(
        segments=[
            SegmentDraft(
                text="First blood. The gate falls.",
                page_refs=[1, 2, 99],
            ),
            SegmentDraft(text="Mira runs. Kaito follows.", page_refs=[3]),
        ]
    )


def test_generate_filters_page_refs(fresh_db, monkeypatch):
    from backend.providers import gemini_vision

    chapter_id = _chapter_with_pages(fresh_db)
    monkeypatch.setattr(gemini_vision, "generate_script", lambda _p, _q, _m: _draft())
    result = script.generate(chapter_id)
    assert result == {"segments": 2}
    ordered = segment_queries.list_ordered(chapter_id)
    assert [seg["position"] for seg in ordered] == [1, 2]
    assert [seg["segment_key"] for seg in ordered] == [
        f"ch{chapter_id}_s001",
        f"ch{chapter_id}_s002",
    ]
    assert json.loads(ordered[0]["page_refs"]) == [1, 2]
    assert all(seg["status"] == "draft" for seg in ordered)


def test_generate_keeps_reviewed_without_confirm(fresh_db, monkeypatch):
    from backend.providers import gemini_vision

    chapter_id = _chapter_with_pages(fresh_db)
    monkeypatch.setattr(gemini_vision, "generate_script", lambda _p, _q, _m: _draft())
    script.generate(chapter_id)
    first = segment_queries.list_ordered(chapter_id)[0]
    script.patch_segment(first["segment_key"], text="Locked text.")
    script.mark_reviewed(chapter_id)
    script.generate(chapter_id)
    ordered = segment_queries.list_ordered(chapter_id)
    reviewed = [seg for seg in ordered if seg["status"] == "reviewed"]
    assert len(reviewed) == 2
    assert reviewed[0]["text"] == "Locked text."
    assert len(ordered) == 4


def test_split_merge_delete_reindex(fresh_db, monkeypatch):
    from backend.providers import gemini_vision

    chapter_id = _chapter_with_pages(fresh_db)
    monkeypatch.setattr(gemini_vision, "generate_script", lambda _p, _q, _m: _draft())
    script.generate(chapter_id)
    key = f"ch{chapter_id}_s001"
    script.split_segment(key)
    ordered = segment_queries.list_ordered(chapter_id)
    assert len(ordered) == 3
    assert [seg["position"] for seg in ordered] == [1, 2, 3]
    assert all(seg["status"] == "draft" for seg in ordered)
    script.merge_next(f"ch{chapter_id}_s001")
    ordered = segment_queries.list_ordered(chapter_id)
    assert len(ordered) == 2
    assert "First blood." in ordered[0]["text"]
    script.delete_segment(f"ch{chapter_id}_s002")
    ordered = segment_queries.list_ordered(chapter_id)
    assert len(ordered) == 1
    assert ordered[0]["position"] == 1
    assert ordered[0]["segment_key"] == f"ch{chapter_id}_s001"


def test_patch_filters_refs_and_sets_draft(fresh_db, monkeypatch):
    from backend.providers import gemini_vision

    chapter_id = _chapter_with_pages(fresh_db)
    monkeypatch.setattr(gemini_vision, "generate_script", lambda _p, _q, _m: _draft())
    script.generate(chapter_id)
    key = f"ch{chapter_id}_s001"
    script.mark_reviewed(chapter_id)
    updated = script.patch_segment(key, text="Edited.", page_refs=[2, 77])
    assert updated["status"] == "draft"
    assert json.loads(updated["page_refs"]) == [2]
    assert segment_queries.has_draft(chapter_id)


def test_review_gate_counts(fresh_db, monkeypatch):
    from backend.providers import gemini_vision

    chapter_id = _chapter_with_pages(fresh_db)
    assert not segment_queries.has_draft(chapter_id)
    monkeypatch.setattr(gemini_vision, "generate_script", lambda _p, _q, _m: _draft())
    script.generate(chapter_id)
    assert segment_queries.has_draft(chapter_id)
    assert script.mark_reviewed(chapter_id) == {"reviewed": 2}
    assert not segment_queries.has_draft(chapter_id)


def test_text_falls_back_to_light_on_quota(fresh_db, monkeypatch):
    from backend.providers import gemini_vision
    from backend.providers.base import ProviderError

    chapter_id = _chapter_with_pages(fresh_db)
    monkeypatch.setenv("TEXT_MODEL", "strong-x")
    monkeypatch.setenv("VISION_MODEL", "light-y")
    calls: list[str] = []

    def fake(payload, prompt, model):
        calls.append(model)
        if model == "strong-x":
            raise ProviderError("rate_limit", "429")
        return _draft()

    monkeypatch.setattr(gemini_vision, "generate_script", fake)
    result = script.generate(chapter_id)
    assert result == {"segments": 2}
    assert calls == ["strong-x", "light-y"]
    from backend.db.queries import costs as cost_queries

    assert cost_queries.calls_today_for_model("light-y") == 1
    assert cost_queries.calls_today_for_model("strong-x") == 0


def test_payload_carries_page_count_without_30k_cut(fresh_db, monkeypatch):
    import json

    from backend.providers import gemini_vision

    chapter_id = _chapter_with_pages(fresh_db)
    seen: dict = {}

    def fake(payload, prompt, model):
        seen["payload"] = payload
        return _draft()

    monkeypatch.setattr(gemini_vision, "generate_script", fake)
    script.generate(chapter_id)
    blob = json.loads(seen["payload"])
    assert blob["page_count"] == 5
    assert len(blob["pages"]) == 5
    assert "truncated" not in blob


def _draft_with_mention():
    from backend.providers.base import SegmentDraft
    from backend.providers.base import ScriptDraft as Draft

    return Draft(
        segments=[
            SegmentDraft(text="Kaito runs through the gate.", page_refs=[1]),
            SegmentDraft(
                text="He learns this the hard way on page 5, screaming.",
                page_refs=[2],
            ),
        ]
    )


def test_page_mention_triggers_single_repair(fresh_db, monkeypatch):
    import json

    from backend.providers import gemini_vision

    chapter_id = _chapter_with_pages(fresh_db)
    monkeypatch.setattr(
        gemini_vision, "generate_script", lambda _p, _q, _m: _draft_with_mention()
    )
    calls: list = []

    def fake_repair(prompt, schema, model):
        calls.append(model)
        return json.dumps({"texts": ["He learns this the hard way, screaming."]})

    monkeypatch.setattr(gemini_vision, "complete_json", fake_repair)
    result = script.generate(chapter_id)
    assert result == {"segments": 2}
    assert len(calls) == 1
    ordered = segment_queries.list_ordered(chapter_id)
    assert ordered[0]["text"] == "Kaito runs through the gate."
    assert ordered[1]["text"] == "He learns this the hard way, screaming."
    assert "page 5" not in ordered[1]["text"]


def test_persistent_mention_fails_with_positions(fresh_db, monkeypatch):
    import json

    from backend.providers import gemini_vision

    chapter_id = _chapter_with_pages(fresh_db)
    monkeypatch.setattr(
        gemini_vision, "generate_script", lambda _p, _q, _m: _draft_with_mention()
    )

    def stubborn(prompt, schema, model):
        return json.dumps({"texts": ["Still on page 5, always."]})

    monkeypatch.setattr(gemini_vision, "complete_json", stubborn)
    try:
        script.generate(chapter_id)
        raise AssertionError("should have raised")
    except ValueError as exc:
        assert "segments [2]" in str(exc)
    assert segment_queries.list_ordered(chapter_id) == []


def test_clean_draft_never_calls_repair(fresh_db, monkeypatch):
    from backend.providers import gemini_vision

    chapter_id = _chapter_with_pages(fresh_db)
    monkeypatch.setattr(gemini_vision, "generate_script", lambda _p, _q, _m: _draft())
    calls: list = []

    def counting(prompt, schema, model):
        calls.append(model)
        raise AssertionError("repair must not run")

    monkeypatch.setattr(gemini_vision, "complete_json", counting)
    assert script.generate(chapter_id) == {"segments": 2}
    assert calls == []


def test_regex_catches_variants():
    bad = [
        "on page 5, he runs",
        "see pages 3 to 5 for proof",
        "as seen in panel 2",
        "told in chapter 12",
        "Page 9 shows it",
    ]
    for text in bad:
        assert script.PAGE_MENTION_RE.search(text), text
    for text in ["the pages turn yellow", "a panel of judges"]:
        assert not script.PAGE_MENTION_RE.search(text), text
