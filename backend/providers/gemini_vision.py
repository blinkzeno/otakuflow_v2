"""Gemini provider (free tier, AI Studio key, no card needed).

Page analysis runs in batches: several labeled page images in one call,
one analysis per image back. Text tasks (synthesis, script) take the
model as a parameter so the caller can route heavy lifting to the
high quota light model and keep the strong model for narrative quality.
"""

import logging

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from backend.core import config
from backend.providers.base import (
    ChapterSummary,
    PageAnalysis,
    ProviderError,
    ScriptDraft,
)

logger = logging.getLogger("otakuflow")


class BatchAnalysis(BaseModel):
    analyses: list[PageAnalysis]


def _client() -> genai.Client:
    key = config.gemini_api_key()
    if not key:
        raise ProviderError("auth", "GEMINI_API_KEY is missing, set it in .env")
    return genai.Client(api_key=key)


def _raise_for_api_error(exc: Exception) -> ProviderError:
    text = str(exc)
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if code == 429 or "429" in text or "RESOURCE_EXHAUSTED" in text:
        return ProviderError("rate_limit", text[:300])
    if code in (401, 403) or "API key" in text:
        return ProviderError("auth", text[:300])
    return ProviderError("network", text[:300])


def _generate(
    prompt: str,
    image_bytes: list[bytes] | None,
    schema: dict,
    model: str,
) -> str:
    client = _client()
    parts: list = [prompt]
    for raw in image_bytes or []:
        parts.append(types.Part.from_bytes(data=raw, mime_type="image/jpeg"))
    try:
        response = client.models.generate_content(
            model=model,
            contents=parts,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
    except Exception as exc:
        raise _raise_for_api_error(exc)
    text = (response.text or "").strip()
    if not text:
        raise ProviderError("invalid", "empty answer from model")
    return text


def analyze_pages(
    images: list[bytes], prompt: str, model: str
) -> tuple[list[PageAnalysis], list[int]]:
    """One call for N pages. Returns (valid analyses, failed batch indexes).

    Raises ProviderError when nothing usable comes back after the retry.
    """
    expected = list(range(1, len(images) + 1))
    raw = _generate(prompt, images, BatchAnalysis.model_json_schema(), model)
    try:
        batch = BatchAnalysis.model_validate_json(raw)
    except ValidationError:
        raw = _generate(
            prompt + "\nReturn valid JSON only.",
            images,
            BatchAnalysis.model_json_schema(),
            model,
        )
        try:
            batch = BatchAnalysis.model_validate_json(raw)
        except ValidationError as exc:
            raise ProviderError("invalid", f"bad JSON after retry: {exc}") from exc
    seen: set[int] = set()
    valid: list[PageAnalysis] = []
    failed: list[int] = []
    for item in batch.analyses:
        index = item.batch_index
        if index not in expected or index in seen:
            failed.append(index if isinstance(index, int) else -1)
            continue
        seen.add(index)
        valid.append(item)
    for missing in expected:
        if missing not in seen:
            failed.append(missing)
    if not valid:
        raise ProviderError("invalid", "no valid page in batch after retry")
    return valid, failed


def synthesize(texts: str, prompt: str, model: str) -> ChapterSummary:
    raw = _generate(
        f"{prompt}\n\nPages:\n{texts}", None, ChapterSummary.model_json_schema(), model
    )
    try:
        return ChapterSummary.model_validate_json(raw)
    except ValidationError:
        fixed = _generate(
            f"{prompt}\nReturn valid JSON only.\n\nPages:\n{texts}",
            None,
            ChapterSummary.model_json_schema(),
            model,
        )
        try:
            return ChapterSummary.model_validate_json(fixed)
        except ValidationError as exc:
            raise ProviderError("invalid", f"bad JSON after retry: {exc}") from exc


def generate_script(summary_json: str, prompt: str, model: str) -> ScriptDraft:
    raw = _generate(
        f"{prompt}\n\nChapter data:\n{summary_json}",
        None,
        ScriptDraft.model_json_schema(),
        model,
    )
    try:
        return ScriptDraft.model_validate_json(raw)
    except ValidationError:
        fixed = _generate(
            f"{prompt}\nReturn valid JSON only.\n\nChapter data:\n{summary_json}",
            None,
            ScriptDraft.model_json_schema(),
            model,
        )
        try:
            return ScriptDraft.model_validate_json(fixed)
        except ValidationError as exc:
            raise ProviderError("invalid", f"bad JSON after retry: {exc}") from exc


def complete_json(prompt: str, schema: dict, model: str) -> str:
    """One schema-constrained call with a single retry. Returns raw JSON.

    The caller validates with its own Pydantic model.
    """
    raw = _generate(prompt, None, schema, model)
    return raw
