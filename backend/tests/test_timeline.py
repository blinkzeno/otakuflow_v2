"""Timeline math from real audio rows, plus settings guardrails."""

import pytest

from backend.db.queries import audio as audio_queries
from backend.db.queries import pages as page_queries
from backend.db.queries import projects as project_queries
from backend.db.queries import segments as segment_queries
from backend.services import timeline as timeline_service
from backend.services import video as video_service


def _chapter(fresh_db):
    _ = fresh_db
    project_id = project_queries.create_project("Render")
    chapter_id = project_queries.create_chapter(project_id, "Render", "r.cbz")
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
            for index in range(1, 4)
        ],
    )
    segment_queries.insert_many(
        chapter_id,
        [
            {
                "position": 1,
                "segment_key": f"ch{chapter_id}_s001",
                "text": "One.",
                "page_refs": "[1, 2]",
                "duration_estimate": 1.0,
                "status": "voiced",
            },
            {
                "position": 2,
                "segment_key": f"ch{chapter_id}_s002",
                "text": "Two.",
                "page_refs": "[3]",
                "duration_estimate": 1.0,
                "status": "voiced",
            },
        ],
    )
    ordered = segment_queries.list_ordered(chapter_id)
    audio_queries.upsert_audio(
        ordered[0]["id"],
        {
            "provider": "edge",
            "voice": "v",
            "rel_path": "projects/1/audio/sg_0001.mp3",
            "duration": 10.0,
            "text_hash": "a",
        },
    )
    audio_queries.upsert_audio(
        ordered[1]["id"],
        {
            "provider": "edge",
            "voice": "v",
            "rel_path": "projects/1/audio/sg_0002.mp3",
            "duration": 20.0,
            "text_hash": "b",
        },
    )
    return chapter_id


def test_timeline_starts_are_cumulative(fresh_db):
    clips = timeline_service.build_timeline(_chapter(fresh_db))
    assert [(c["start"], c["duration"]) for c in clips] == [(0.0, 10.0), (10.0, 20.0)]
    assert timeline_service.timeline_total(clips) == 30.0
    assert [p["index"] for p in clips[0]["pages"]] == [1, 2]


def test_timeline_refuses_missing_audio(fresh_db):
    from backend.db.queries import segments as segment_queries

    chapter_id = _chapter(fresh_db)
    ordered = segment_queries.list_ordered(chapter_id)
    audio_queries.upsert_audio(
        ordered[0]["id"],
        {
            "provider": "edge",
            "voice": "v",
            "rel_path": "x.mp3",
            "duration": 0.0,
            "text_hash": "a",
        },
    )
    with pytest.raises(ValueError, match="no audio"):
        timeline_service.build_timeline(chapter_id)


def test_settings_guardrails():
    good = video_service.validate_settings(None)
    assert good["preset"] == "veryfast"
    assert video_service.validate_settings({"crf": 23})["crf"] == 23
    with pytest.raises(ValueError, match="preset"):
        video_service.validate_settings({"preset": "; rm -rf"})
    with pytest.raises(ValueError, match="crf"):
        video_service.validate_settings({"crf": 99})
    with pytest.raises(ValueError, match="unknown"):
        video_service.validate_settings({"codec": "x"})
