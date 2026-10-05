"""Smart montage: focus boxes, settings, 16:9 crop, blur fill."""

import json

from backend.services import timeline as timeline_service
from backend.services import video as video_service


def _page(analysis: dict) -> dict:
    return {"analysis_json": json.dumps(analysis)}


def test_focus_box_accepted():
    box = timeline_service.page_focus(
        _page({"focus": {"x": 100, "y": 200, "w": 400, "h": 500}})
    )
    assert box == {"x": 100, "y": 200, "w": 400, "h": 500}


def test_full_frame_means_no_focus():
    assert (
        timeline_service.page_focus(
            _page({"focus": {"x": 0, "y": 0, "w": 1000, "h": 1000}})
        )
        is None
    )


def test_garbage_focus_means_no_focus():
    assert timeline_service.page_focus(_page({"focus": {"x": "left"}})) is None
    assert timeline_service.page_focus(_page({})) is None
    assert timeline_service.page_focus({"analysis_json": "not json"}) is None


def test_tiny_box_rejected_at_render():
    assert timeline_service.page_focus(_page({"x": 0, "y": 0})) is None


def test_settings_extended_defaults():
    settings = video_service.validate_settings(None)
    assert settings["kenburns"] is True
    assert "smart_crop" not in settings
    assert "xfade" not in settings


def test_settings_reject_bad_montage_values():
    import pytest

    with pytest.raises(ValueError, match="unknown"):
        video_service.validate_settings({"xfade": 99})
    with pytest.raises(ValueError, match="unknown"):
        video_service.validate_settings({"nope": 1})
    with pytest.raises(ValueError, match="unknown"):
        video_service.validate_settings({"burn_subtitles": True})


def test_prompt_avoids_bubbles():
    from pathlib import Path

    text = (
        Path(__file__).resolve().parent.parent
        / "prompts"
        / "analyze_pages.txt"
    ).read_text(encoding="utf-8")
    assert "Avoid speech bubbles" in text
    assert "ARTWORK" in text


def test_page_clip_zooms_by_default(tmp_path, monkeypatch):
    captured: list = []

    def fake_run(cmd: list[str], timeout: int = 600) -> None:
        captured.append(" ".join(cmd))

    monkeypatch.setattr(video_service, "_run", fake_run)
    out = tmp_path / "clip.mp4"
    settings = video_service.validate_settings(None)
    video_service._page_clip(tmp_path / "in.png", 2.0, settings, out)
    assert "zoompan" in captured[0]
    settings["kenburns"] = False
    video_service._page_clip(tmp_path / "in.png", 2.0, settings, out)
    assert "zoompan" not in captured[1]
    assert "force_original_aspect_ratio" in captured[1]


def test_framed_regions_end_to_end(tmp_path, fresh_db, monkeypatch):
    """_regions_for_page + _still produisent un still plein cadre."""
    from pathlib import Path

    from PIL import Image

    from backend.storage import paths

    _ = fresh_db
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    workdir = Path(str(tmp_path / "work"))
    workdir.mkdir()
    source = paths.page_path(1, "p_0001.jpg")
    source.parent.mkdir(parents=True, exist_ok=True)
    import os as _os

    frame = Image.frombytes("L", (496, 1200), _os.urandom(496 * 1200)).convert("RGB")
    frame.save(source, "JPEG")
    loaded = video_service._load_frame("projects/1/pages/p_0001.jpg")
    page = {"focus_regions": [{"x": 50, "y": 50, "w": 400, "h": 500, "order": 1}]}
    regions = video_service._regions_for_page(loaded, page, "2:3")
    assert len(regions) == 1
    still = video_service._still(loaded, regions[0], "2:3", workdir)
    with Image.open(still) as image:
        assert image.size == (video_service.FRAME_WIDTH, video_service.FRAME_HEIGHT)
    loaded.close()


def test_crop_box_via_regions():
    left, top, right, bottom = video_service._crop_box(
        496, 2560, "2:3", (50.0, 100.0, 450.0, 800.0)
    )
    assert 0 <= left < right <= 496
    assert 0 <= top < bottom <= 2560
    assert left <= 50.0 and top <= 100.0
    assert right >= 450.0 and bottom >= 800.0


def test_crop_ratio_rejected():
    import pytest

    with pytest.raises(ValueError, match="crop_ratio"):
        video_service.validate_settings({"crop_ratio": "5:7"})
