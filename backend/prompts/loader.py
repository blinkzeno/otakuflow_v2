"""Versioned AI prompts. Loaded once, fail fast when unreadable."""

from pathlib import Path

_DIR = Path(__file__).resolve().parent
_cache: dict[str, str] = {}


def get(name: str) -> str:
    if name not in _cache:
        target = _DIR / f"{name}.txt"
        if not target.exists():
            raise RuntimeError(f"prompt file missing: {name}.txt")
        text = target.read_text(encoding="utf-8").strip()
        if not text:
            raise RuntimeError(f"prompt file empty: {name}.txt")
        _cache[name] = text
    return _cache[name]
