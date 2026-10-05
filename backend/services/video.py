"""MP4 render: still pages plus voice, gentle zoom, concat join.

One clip per segment. A segment spanning several pages shares its time
evenly, the voice keeps playing across the page change. Settings are
whitelisted, the ffmpeg command is built as an argument list, never a
shell string.

Smart crop frames the analysis focus box reshaped to 16:9, on a blurred
fill of the same page, CapCut style. No focus means full page, same
blurred fill, never black bars.
"""

import logging
import math
import shutil
import subprocess
import uuid
from collections.abc import Callable
from pathlib import Path

from mutagen.mp4 import MP4
from PIL import Image, ImageFilter, ImageOps, ImageStat

from backend.core import config
from backend.db.queries import renders as render_queries
from backend.db.queries import segments as segment_queries
from backend.services import timeline as timeline_service
from backend.services.jobs import JobCancelled
from backend.storage import paths

logger = logging.getLogger("otakuflow")

PRESETS = {
    "ultrafast", "superfast", "veryfast", "faster",
    "fast", "medium", "slow", "slower", "veryslow",
}

DEFAULT_SETTINGS = {
    "width": 1920,
    "height": 1080,
    "fps": 30,
    "crf": 20,
    "preset": "veryfast",
    "kenburns": True,
    "crop_ratio": "2:3",
}

FRAME_WIDTH = 3840
FRAME_HEIGHT = 2160
BLUR_RADIUS = 40
BLUR_DARKEN = 0.6
FOCUS_PAD = 0.06          # marge autour du focus (fraction de sa taille)
MIN_CROP_W = 0.6          # largeur mini du crop (fraction de la page) = zoom max
KENBURNS_END = 1.06       # zoom final du Ken Burns (centré)
MIN_REGION_SECONDS = 1.5  # durée mini d'un plan
BLANK_STDDEV = 6.0        # en dessous, une bande est considérée vide
CROP_RATIOS = {"2:3", "9:16", "3:4", "1:1", "4:3", "16:9"}
WHITE_LEVEL = 235          # au-dessus = pixel blanc
MID_LOW, MID_HIGH = 40, 215  # tons moyens : dessin, quasi absents du texte noir sur blanc
PAPER_WHITE_MIN = 0.30     # une ligne "papier" a au moins 30 % de blanc...
PAPER_MID_MAX = 0.15       # ...et moins de 15 % de tons moyens
ART_MIN_SHARE = 0.25       # sous 25 % de lignes de dessin, la zone est du texte seul
WIDE_LIMIT = 16 / 9        # hauteur mini d'un crop = largeur / WIDE_LIMIT
SKIP_KINDS = {"credits", "ad", "blank"}

Region = tuple[float, float, float, float]  # x0, y0, x1, y1 en pixels de la page


def validate_settings(raw: dict | None) -> dict:
    settings = dict(DEFAULT_SETTINGS)
    for key, value in (raw or {}).items():
        if key not in DEFAULT_SETTINGS:
            raise ValueError(f"unknown render setting: {key}")
        settings[key] = value
    if settings["preset"] not in PRESETS:
        raise ValueError(f"bad preset: {settings['preset']}")
    if not 0 <= int(settings["crf"]) <= 51:
        raise ValueError("crf must be 0-51")
    if not 1 <= int(settings["fps"]) <= 60:
        raise ValueError("fps must be 1-60")
    if int(settings["width"]) not in (1280, 1920):
        raise ValueError("width must be 1280 or 1920")
    if int(settings["height"]) not in (720, 1080):
        raise ValueError("height must be 720 or 1080")
    if settings["crop_ratio"] not in CROP_RATIOS:
        raise ValueError(f"crop_ratio must be one of {sorted(CROP_RATIOS)}")
    settings["kenburns"] = bool(settings["kenburns"])
    return settings


def _ffmpeg() -> str:
    override = (config.ffmpeg_path() or "").strip()
    if override:
        return override
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def _run(cmd: list[str], timeout: int = 900) -> None:
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=True)
    except subprocess.CalledProcessError as exc:
        tail = (exc.stderr or "")[-2000:]
        try:
            tail = tail.replace(str(paths.data_root()), "data/")
        except Exception:
            pass
        raise ValueError(f"ffmpeg failed: {tail}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ValueError("ffmpeg timed out on a clip") from exc


def _num(value: object, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _is_blank(tile: Image.Image) -> bool:
    return ImageStat.Stat(tile.convert("L")).stddev[0] < BLANK_STDDEV


def _row_flags(gray: Image.Image) -> list[bool]:
    """Une valeur par ligne : True = dessin, False = papier (blanc + texte)."""
    height = gray.height
    white = gray.point(lambda v: 255 if v > WHITE_LEVEL else 0).resize((1, height), Image.BOX).tobytes()
    mid = gray.point(lambda v: 255 if MID_LOW < v < MID_HIGH else 0).resize((1, height), Image.BOX).tobytes()
    white_min, mid_max = int(PAPER_WHITE_MIN * 255), int(PAPER_MID_MAX * 255)
    return [not (white[i] >= white_min and mid[i] < mid_max) for i in range(height)]


def _trim_to_art(frame: Image.Image, rect: Region) -> Region | None:
    """Retire le papier en haut et en bas de la zone. None si c'est du texte seul."""
    x0, y0, x1, y1 = (int(value) for value in rect)
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None
    flags = _row_flags(frame.crop((x0, y0, x1, y1)).convert("L"))
    total = len(flags)
    if sum(flags) < ART_MIN_SHARE * total:
        return None
    window = max(12, (x1 - x0) // 20)

    def solid(chunk: list[bool]) -> bool:
        return bool(chunk) and sum(chunk) >= 0.7 * len(chunk)

    top = 0
    while top < total and not solid(flags[top : top + window]):
        top += 1
    bottom = total
    while bottom > top and not solid(flags[max(bottom - window, 0) : bottom]):
        bottom -= 1
    if bottom - top < 8:
        return None
    return (float(x0), float(y0 + top), float(x1), float(y0 + bottom))


def _art_regions(frame: Image.Image, ratio: str) -> list[Region]:
    """Séquences de dessin d'une page, séparées par des bandes de papier. Peut être vide."""
    flags = _row_flags(frame.convert("L"))
    min_gap = max(8, frame.width // 12)   # papier plus court = même séquence
    min_run = max(8, frame.width // 8)    # séquence plus courte = bruit (trait, bordure)
    runs: list[tuple[int, int]] = []
    start: int | None = None
    end = gap = 0
    for y, is_art in enumerate(flags):
        if is_art:
            if start is None:
                start = y
            end, gap = y + 1, 0
        elif start is not None:
            gap += 1
            if gap >= min_gap:
                runs.append((start, end))
                start = None
    if start is not None:
        runs.append((start, end))
    target_w, target_h = (int(part) for part in ratio.split(":"))
    max_h = round(frame.width * target_h / target_w) * 1.6
    regions: list[Region] = []
    for run_start, run_end in runs:
        if run_end - run_start < min_run:
            continue
        parts = max(1, math.ceil((run_end - run_start) / max_h))
        size = (run_end - run_start) / parts
        for index in range(parts):
            regions.append(
                (0.0, run_start + index * size, float(frame.width), run_start + (index + 1) * size)
            )
    return regions


def _rect_from_focus(raw: object, width: int, height: int) -> Region | None:
    """Focus 0-1000 -> rectangle en pixels avec marge, ou None si inutilisable."""
    if not isinstance(raw, dict):
        return None
    try:
        x, y, w, h = (float(raw[key]) for key in ("x", "y", "w", "h"))
    except (KeyError, TypeError, ValueError):
        return None
    x, y = min(max(x, 0.0), 1000.0), min(max(y, 0.0), 1000.0)
    w, h = min(w, 1000.0 - x), min(h, 1000.0 - y)
    if w < 50 or h < 50:
        return None
    pad_w, pad_h = w * FOCUS_PAD, h * FOCUS_PAD
    x0, y0 = max(x - pad_w, 0.0), max(y - pad_h, 0.0)
    x1, y1 = min(x + w + pad_w, 1000.0), min(y + h + pad_h, 1000.0)
    return (x0 / 1000 * width, y0 / 1000 * height, x1 / 1000 * width, y1 / 1000 * height)


def _auto_tiles(frame: Image.Image, ratio: str) -> list[Region]:
    """Découpe une page haute en tuiles au ratio demandé, sans les bandes blanches."""
    full: Region = (0.0, 0.0, float(frame.width), float(frame.height))
    target_w, target_h = (int(part) for part in ratio.split(":"))
    tile_h = max(1, round(frame.width * target_h / target_w))
    if frame.height <= tile_h * 1.3:
        return [full]
    step = max(1, int(tile_h * 0.92))  # léger recouvrement
    tops = list(range(0, frame.height - tile_h, step)) + [frame.height - tile_h]
    tiles: list[Region] = []
    for top in tops:
        strip = frame.crop((0, top, frame.width, top + tile_h))
        if not _is_blank(strip):
            tiles.append((0.0, float(top), float(frame.width), float(top + tile_h)))
    return tiles or [full]


def _regions_for_page(frame: Image.Image, page: dict, ratio: str) -> list[Region]:
    """Plans de dessin d'une page, dans l'ordre de lecture. Peut être vide (page de texte seul)."""
    raw = page.get("focus_regions")
    if not isinstance(raw, list) or not raw:
        legacy = page.get("focus")
        raw = [legacy] if isinstance(legacy, dict) else []
    items = [item for item in raw if isinstance(item, dict)]
    if any(item.get("kind") != "text" for item in items):
        items = [item for item in items if item.get("kind") != "text"]
    items.sort(key=lambda item: _num(item.get("order"), 0.0))
    rects: list[Region] = []
    for item in items:
        rect = _rect_from_focus(item, frame.width, frame.height)
        rect = _trim_to_art(frame, rect) if rect else None
        if rect is not None:
            rects.append(rect)
    tall = frame.height > frame.width * 2
    unusable = len(rects) == 1 and tall and (rects[0][3] - rects[0][1]) > 0.7 * frame.height
    if rects and not unusable:
        return rects
    return _art_regions(frame, ratio)


def _crop_box(width: int, height: int, ratio: str, rect: Region) -> tuple[int, int, int, int]:
    """Fenêtre qui contient tout le rectangle sans l'étendre pour atteindre un ratio.

    Le ratio est une limite portrait : si la zone est plus haute que large,
    on élargit (côtés de la page) ; si elle est plus large que haute, on garde sa hauteur.
    """
    target_w, target_h = (int(part) for part in ratio.split(":"))
    ratio_value = target_w / target_h
    fx0, fy0, fx1, fy1 = rect
    focus_w, focus_h = fx1 - fx0, fy1 - fy0
    crop_w = min(max(focus_w, width * MIN_CROP_W), float(width))
    crop_h = min(max(focus_h, crop_w / WIDE_LIMIT), float(height))
    if crop_w / crop_h < ratio_value:
        crop_w = min(crop_h * ratio_value, float(width))
    cw, ch = max(1, int(crop_w)), max(1, int(crop_h))
    center_x, center_y = (fx0 + fx1) / 2, (fy0 + fy1) / 2
    left = min(max(int(center_x - cw / 2), 0), width - cw)
    top = min(max(int(center_y - ch / 2), 0), height - ch)
    return (left, top, left + cw, top + ch)


def _blurred_fill(frame: Image.Image) -> Image.Image:
    """Fond flou calculé en petit puis agrandi (rapide), assombri."""
    small_w, small_h = FRAME_WIDTH // 8, FRAME_HEIGHT // 8
    scale = max(small_w / frame.width, small_h / frame.height)
    cover = frame.resize(
        (max(1, round(frame.width * scale)), max(1, round(frame.height * scale))),
        Image.BILINEAR,
    )
    left, top = (cover.width - small_w) // 2, (cover.height - small_h) // 2
    cover = cover.crop((left, top, left + small_w, top + small_h))
    cover = cover.filter(ImageFilter.GaussianBlur(BLUR_RADIUS / 8))
    return cover.resize((FRAME_WIDTH, FRAME_HEIGHT), Image.BICUBIC).point(
        lambda value: int(value * BLUR_DARKEN)
    )


def _open_frame(source: Path) -> Image.Image:
    with Image.open(source) as handle:
        handle.load()
        return ImageOps.exif_transpose(handle).convert("RGB")


def _load_frame(page_rel: str) -> Image.Image:
    source = paths.safe_join(*page_rel.split("/"))
    if not source.exists():
        raise ValueError(f"page image missing: {page_rel}")
    return _open_frame(source)


def _still(frame: Image.Image, rect: Region, ratio: str, workdir: Path) -> Path:
    """Crop qui contient tout le rectangle, centré sur un fond flou. Aucun zoom ajouté."""
    box = _crop_box(frame.width, frame.height, ratio, rect)
    cropped = frame.crop(box)
    canvas = _blurred_fill(cropped)
    scale = min(FRAME_WIDTH / cropped.width, FRAME_HEIGHT / cropped.height)
    sized = cropped.resize(
        (max(1, round(cropped.width * scale)), max(1, round(cropped.height * scale))),
        Image.LANCZOS,
    )
    canvas.paste(sized, ((FRAME_WIDTH - sized.width) // 2, (FRAME_HEIGHT - sized.height) // 2))
    target = workdir / f"{uuid.uuid4().hex}.png"
    canvas.save(target, "PNG")
    return target


def _page_clip(
    still: Path, seconds: float, settings: dict, out: Path, zoom_out: bool = False
) -> None:
    fps = int(settings["fps"])
    width, height = settings["width"], settings["height"]
    if settings["kenburns"]:
        frames = max(1, round(seconds * fps))
        gain = min(0.10, (KENBURNS_END - 1.0) + 0.004 * max(seconds - 6.0, 0.0))
        if zoom_out:
            zoom = f"1+{gain:.4f}*(1-on/{frames})"
        else:
            zoom = f"1+{gain:.4f}*on/{frames}"
        filt = (
            f"zoompan=z='{zoom}'"
            ":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s={width}x{height}:fps={fps}"
        )
        cmd = [
            _ffmpeg(), "-y", "-i", str(still), "-vf", filt,
            "-frames:v", str(frames), "-c:v", "libx264",
            "-crf", str(settings["crf"]), "-preset", str(settings["preset"]),
            "-pix_fmt", "yuv420p", str(out),
        ]
    else:
        filt = (
            f"scale={settings['width']}:{settings['height']}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={settings['width']}:{settings['height']}:"
            "(ow-iw)/2:(oh-ih)/2"
        )
        cmd = [
            _ffmpeg(), "-y", "-loop", "1", "-i", str(still), "-vf", filt,
            "-t", str(seconds), "-r", str(settings["fps"]),
            "-c:v", "libx264",
            "-crf", str(settings["crf"]), "-preset", str(settings["preset"]),
            "-pix_fmt", "yuv420p", str(out),
        ]
    _run(cmd)


def _mux(video: Path, audio_rel: str, out: Path) -> None:
    audio = paths.safe_join(*audio_rel.split("/"))
    _run([
        _ffmpeg(), "-y", "-i", str(video), "-i", str(audio),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-shortest", str(out),
    ])


def _concat(parts: list[Path], out: Path) -> None:
    listing = parts[0].parent / "list.txt"
    listing.write_text(
        "".join(f"file '{part.name}'\n" for part in parts), encoding="utf-8"
    )
    _run([
        _ffmpeg(), "-y", "-f", "concat", "-safe", "0",
        "-i", str(listing), "-c", "copy", str(out),
    ])


def _union(first: Region, second: Region) -> Region:
    return (
        min(first[0], second[0]), min(first[1], second[1]),
        max(first[2], second[2]), max(first[3], second[3]),
    )


def _reduce(items: list[tuple[int, Region]], limit: int) -> list[tuple[int, Region]]:
    """Fusionne les plans voisins d'une même page quand le segment est trop court."""
    items = list(items)
    while len(items) > limit:
        for index in range(len(items) - 1):
            if items[index][0] == items[index + 1][0]:
                merged = _union(items[index][1], items[index + 1][1])
                items[index : index + 2] = [(items[index][0], merged)]
                break
        else:
            break
    return items


def _segment_clips(
    clip: dict, rel_by_id: dict, cfg: dict, workdir: Path, position: int
) -> list[Path]:
    """Un sous-clip muet par plan de dessin, durée du segment partagée à parts égales."""
    ratio = cfg["crop_ratio"]
    pages = clip["pages"]
    frames: list[Image.Image] = []
    for page in pages:
        page_rel = rel_by_id.get(page["id"])
        if page_rel is None:
            raise ValueError(f"page {page['id']} is gone")
        frames.append(_load_frame(page_rel))

    def collect(skip_non_story: bool) -> list[tuple[int, Region]]:
        found: list[tuple[int, Region]] = []
        for page_pos, page in enumerate(pages):
            if skip_non_story and page.get("page_kind") in SKIP_KINDS:
                continue
            found += [(page_pos, rect) for rect in _regions_for_page(frames[page_pos], page, ratio)]
        return found

    items = collect(True) or collect(False)
    if not items:  # aucun dessin détecté : dernier recours, tuiles simples
        for page_pos, frame in enumerate(frames):
            items += [(page_pos, rect) for rect in _auto_tiles(frame, ratio)]
    limit = max(1, int(clip["duration"] // MIN_REGION_SECONDS))
    items = _reduce(items, limit)
    share = clip["duration"] / len(items)
    videos: list[Path] = []
    for number, (page_pos, rect) in enumerate(items, start=1):
        still = _still(frames[page_pos], rect, ratio, workdir)
        silent = workdir / f"clip_{position}_{number}.mp4"
        _page_clip(still, share, cfg, silent, zoom_out=(number % 2 == 0))
        still.unlink(missing_ok=True)
        videos.append(silent)
    for frame in frames:
        frame.close()
    return videos


def render_chapter(
    chapter_id: int,
    settings: dict | None = None,
    progress: Callable[[int, int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> dict:
    from backend.db.queries import audio as audio_queries
    from backend.db.queries import pages as page_queries
    from backend.db.queries import projects as project_queries
    from backend.services.tts import text_hash

    report = progress or (lambda _done, _total: None)
    stop = should_stop or (lambda: False)
    chapter = project_queries.get_chapter(chapter_id)
    if chapter is None:
        raise ValueError("chapter not found")
    project_id = int(chapter["project_id"])
    if segment_queries.has_draft(chapter_id):
        raise ValueError("script not reviewed, lock it first")
    cfg = validate_settings(settings)
    clips = timeline_service.build_timeline(chapter_id)
    for clip in clips:
        segment = next(
            seg
            for seg in segment_queries.list_ordered(chapter_id)
            if seg["segment_key"] == clip["segment_key"]
        )
        current = audio_queries.get_by_segment(segment["id"])
        if current is None or current["text_hash"] != text_hash(segment["text"]):
            raise ValueError(f"segment {clip['segment_key']} audio is stale")
    rel_by_id = {
        page["id"]: str(page["rel_path"])
        for page in page_queries.list_pages(chapter_id)
    }
    render_id = render_queries.create_render(chapter_id, cfg)
    workdir = paths.safe_join("projects", str(project_id), "renders", f".tmp_{render_id}")
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        parts: list[Path] = []
        for position, clip in enumerate(clips, start=1):
            if stop():
                raise JobCancelled()
            page_videos = _segment_clips(clip, rel_by_id, cfg, workdir, position)
            if len(page_videos) > 1:
                joined = workdir / f"seg_{position}.mp4"
                _concat(page_videos, joined)
                for extra in page_videos:
                    extra.unlink(missing_ok=True)
            else:
                joined = page_videos[0]
            final = workdir / f"final_{position}.mp4"
            _mux(joined, clip["audio_rel"], final)
            joined.unlink(missing_ok=True)
            parts.append(final)
            report(position, len(clips))
        output = paths.render_path(project_id, "final.mp4")
        _concat(parts, output)
        actual = float(MP4(output).info.length)
        want = timeline_service.timeline_total(clips)
        if abs(actual - want) > 1.0:
            raise ValueError(f"render length off: got {actual:.1f}s want {want:.1f}s")
        import json

        render_queries.complete_render(
            render_id,
            json.dumps(clips),
            f"projects/{project_id}/renders/final.mp4",
            "done",
        )
        logger.info("[render] chapter=%s seconds=%s", chapter_id, want)
        return {"render_id": render_id, "seconds": want}
    except Exception:
        render_queries.complete_render(render_id, "[]", None, "failed")
        raise
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
