"""Provider contracts and validated AI outputs.

Every AI output is validated by Pydantic BEFORE any database write.
Scores and indexes stay server computed, never trusted from the model.
"""

from pydantic import BaseModel, Field


class ProviderError(Exception):
    """kind is one of: rate_limit | invalid | auth | network."""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


class Dialogue(BaseModel):
    speaker: str | None = None
    text: str


class FocusRegion(BaseModel):
    x: float = 0.0
    y: float = 0.0
    w: float = 1000.0
    h: float = 1000.0
    order: int = 1
    kind: str = "art"


class PageAnalysis(BaseModel):
    batch_index: int = Field(default=0, ge=0)
    characters: list[str] = []
    actions: list[str] = []
    dialogues: list[Dialogue] = []
    events: list[str] = []
    location: str = ""
    importance: int = Field(ge=0, le=10)
    summary: str
    visual_description: str = ""
    focus: FocusRegion = FocusRegion()
    focus_regions: list[FocusRegion] = []
    page_kind: str = "story"
    suggest_zoom: float = Field(default=1.0, ge=1.0, le=2.0)


class ChapterSummary(BaseModel):
    main_characters: list[str] = []
    plot_summary: str
    key_events: list[str] = []
    tone: str = ""


class SegmentDraft(BaseModel):
    text: str
    page_refs: list[int] = []


class ScriptDraft(BaseModel):
    segments: list[SegmentDraft]
