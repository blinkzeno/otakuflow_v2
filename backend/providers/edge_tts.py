"""Edge-TTS provider: free neural voices, no key, no card.

Unofficial Microsoft Edge endpoint: fast and good enough to publish,
but without SLA. Version pinned in requirements, one retry, then the
segment is marked failed and the chapter moves on.
"""

import asyncio
import logging

import edge_tts

logger = logging.getLogger("otakuflow")


class TTSError(Exception):
    pass


async def _fetch(text: str, voice: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice)
    chunks: list[bytes] = []
    async for piece in communicate.stream():
        if piece.get("type") == "audio":
            chunks.append(piece.get("data", b""))
    return b"".join(chunks)


def synthesize(text: str, voice: str, timeout: int = 60) -> bytes:
    if not text.strip():
        raise ValueError("empty text, nothing to synthesize")
    last: Exception | None = None
    for attempt in (1, 2):
        try:
            raw = asyncio.run(asyncio.wait_for(_fetch(text, voice), timeout))
            if not raw:
                raise TTSError("empty audio from edge-tts")
            return raw
        except ValueError:
            raise
        except Exception as exc:
            last = exc
            logger.warning("[tts] attempt %s failed: %s", attempt, exc)
    raise TTSError(f"edge-tts failed twice: {last}")
