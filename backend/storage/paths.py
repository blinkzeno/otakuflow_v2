"""Disk layout under DATA_DIR. Only way to build a file path.

Every path goes through safe_join, which rejects escapes. Callers never
join paths by hand.
"""

from pathlib import Path

from backend.core import config

SUBDIRS = ("originals", "pages", "thumbs", "audio", "renders", "logs", "tmp")


def data_root() -> Path:
    return config.data_root()


def safe_join(*parts: str) -> Path:
    for part in parts:
        candidate = Path(part)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError(f"unsafe path part: {part!r}")
    resolved = (data_root() / Path(*parts)).resolve()
    if not resolved.is_relative_to(data_root()):
        raise ValueError(f"path escapes DATA_DIR: {parts!r}")
    return resolved


def project_dir(project_id: int) -> Path:
    return safe_join("projects", str(project_id))


def ensure_project_dirs(project_id: int) -> Path:
    base = project_dir(project_id)
    for sub in SUBDIRS:
        (base / sub).mkdir(parents=True, exist_ok=True)
    return base


def page_path(project_id: int, filename: str) -> Path:
    return safe_join("projects", str(project_id), "pages", filename)


def thumb_path(project_id: int, filename: str) -> Path:
    return safe_join("projects", str(project_id), "thumbs", filename)


def audio_path(project_id: int, filename: str) -> Path:
    return safe_join("projects", str(project_id), "audio", filename)


def render_path(project_id: int, filename: str) -> Path:
    return safe_join("projects", str(project_id), "renders", filename)


def log_path(project_id: int, filename: str) -> Path:
    return safe_join("projects", str(project_id), "logs", filename)
