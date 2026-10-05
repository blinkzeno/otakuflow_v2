import os
from pathlib import Path

from PIL import Image, ImageDraw

from backend.services import video


def _noise(width: int, height: int) -> Image.Image:
    return Image.frombytes("L", (width, height), os.urandom(width * height)).convert("RGB")


def _webtoon() -> Image.Image:
    page = Image.new("RGB", (496, 2560), "white")
    page.paste(_noise(496, 600), (0, 0))
    page.paste(_noise(496, 660), (0, 1900))
    return page


def test_crop_contains_focus_and_stays_inside_image():
    rect = (50.0, 100.0, 450.0, 800.0)
    left, top, right, bottom = video._crop_box(496, 2560, "2:3", rect)
    assert 0 <= left < right <= 496
    assert 0 <= top < bottom <= 2560
    assert left <= rect[0] and top <= rect[1]
    assert right >= rect[2] and bottom >= rect[3]


def test_crop_is_never_a_thin_strip():
    left, top, right, bottom = video._crop_box(496, 2560, "4:3", (100.0, 200.0, 300.0, 260.0))
    assert (right - left) >= 496 * video.MIN_CROP_W - 1


def test_invalid_focus_is_ignored():
    for bad in ({"x": 0, "y": 0, "w": 0, "h": 0}, {"x": "a"}, None, []):
        assert video._rect_from_focus(bad, 496, 2560) is None


def test_full_page_focus_falls_back_to_tiles_without_blank_bands():
    frame = _webtoon()
    page = {"focus": {"x": 0, "y": 0, "w": 1000, "h": 1000}}
    regions = video._regions_for_page(frame, page, "2:3")
    assert len(regions) >= 2
    for x0, y0, x1, y1 in regions:
        assert not video._is_blank(frame.crop((int(x0), int(y0), int(x1), int(y1))))


def test_regions_follow_reading_order():
    frame = _webtoon()
    page = {
        "focus_regions": [
            {"x": 50, "y": 750, "w": 900, "h": 240, "order": 2},
            {"x": 50, "y": 20, "w": 900, "h": 200, "order": 1},
        ]
    }
    regions = video._regions_for_page(frame, page, "2:3")
    assert len(regions) == 2
    assert regions[0][1] < regions[1][1]


def test_still_is_full_frame(tmp_path: Path):
    frame = _webtoon()
    out = video._still(frame, (0.0, 0.0, 496.0, 744.0), "2:3", tmp_path)
    with Image.open(out) as image:
        assert image.size == (video.FRAME_WIDTH, video.FRAME_HEIGHT)


def _text_block(page: Image.Image, y0: int, y1: int) -> None:
    draw = ImageDraw.Draw(page)
    for y in range(y0, y1, 40):
        draw.rectangle((60, y, 60 + 230 + (y % 80), y + 22), fill="black")


def _page_with_text_and_art() -> Image.Image:
    page = Image.new("RGB", (496, 2560), "white")
    _text_block(page, 20, 300)
    page.paste(_noise(496, 600), (0, 300))
    _text_block(page, 920, 1080)
    page.paste(_noise(496, 400), (0, 1100))
    _text_block(page, 1520, 2500)
    return page


def test_art_regions_skip_text_bands():
    regions = video._art_regions(_page_with_text_and_art(), "2:3")
    assert len(regions) == 2
    assert abs(regions[0][1] - 300) < 20 and abs(regions[0][3] - 900) < 20
    assert abs(regions[1][1] - 1100) < 20 and abs(regions[1][3] - 1500) < 20


def test_text_only_page_has_no_regions():
    page = Image.new("RGB", (496, 2560), "white")
    _text_block(page, 0, 2560)
    assert video._art_regions(page, "2:3") == []
    assert video._trim_to_art(page, (0.0, 0.0, 496.0, 2560.0)) is None


def test_text_kind_regions_are_dropped_when_art_exists():
    page = Image.new("RGB", (496, 2560), "white")
    _text_block(page, 0, 700)
    page.paste(_noise(496, 700), (0, 800))
    data = {
        "focus_regions": [
            {"x": 20, "y": 10, "w": 960, "h": 250, "order": 1, "kind": "text"},
            {"x": 20, "y": 300, "w": 960, "h": 300, "order": 2, "kind": "art"},
        ]
    }
    regions = video._regions_for_page(page, data, "2:3")
    assert len(regions) == 1
    assert regions[0][1] >= 780


def test_crop_does_not_add_height_to_reach_ratio():
    # zone de dessin large et basse : la hauteur reste celle de la zone (plancher 16:9)
    left, top, right, bottom = video._crop_box(496, 2560, "2:3", (0.0, 1100.0, 496.0, 1500.0))
    assert bottom - top == 400
    left, top, right, bottom = video._crop_box(496, 2560, "2:3", (0.0, 1100.0, 496.0, 1150.0))
    assert bottom - top == int(496 / video.WIDE_LIMIT)
