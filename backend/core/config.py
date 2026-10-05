"""Typed access to server settings.

Values come from process env (file .env is loaded when present).
Nothing here is ever sent to the browser.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


load_dotenv(repo_root() / ".env")


def data_dir() -> str:
    return os.getenv("DATA_DIR", "./data")


def data_root() -> Path:
    raw = os.getenv("DATA_DIR", "./data")
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    return (repo_root() / candidate).resolve()


def host() -> str:
    return os.getenv("HOST", "127.0.0.1")


def port() -> int:
    return int(os.getenv("PORT", "8000"))


def max_upload_mb() -> int:
    return int(os.getenv("MAX_UPLOAD_MB", "500"))


def min_interval() -> float:
    return float(os.getenv("VISION_MIN_INTERVAL_SEC", "5"))


def job_workers() -> int:
    return int(os.getenv("JOB_WORKERS", "2"))


def gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "")


def vision_model() -> str:
    return os.getenv("VISION_MODEL", "gemini-3.5-flash-lite")


def text_model() -> str:
    return os.getenv("TEXT_MODEL", "gemini-3.8-flash")


def daily_cap() -> int:
    return int(os.getenv("VISION_DAILY_CAP", "500"))


def text_daily_cap() -> int:
    return int(os.getenv("TEXT_DAILY_CAP", "20"))


def pages_per_call() -> int:
    try:
        size = int(os.getenv("VISION_PAGES_PER_CALL", "8"))
    except ValueError:
        raise ValueError("VISION_PAGES_PER_CALL must be an integer 1-10")
    if not 1 <= size <= 10:
        raise ValueError("VISION_PAGES_PER_CALL must be an integer 1-10")
    return size


def validate_startup() -> None:
    pages_per_call()


def tts_voice() -> str:
    return os.getenv("EDGE_TTS_VOICE", "en-US-AriaNeural")


def ffmpeg_path() -> str:
    return os.getenv("FFMPEG_PATH", "")
