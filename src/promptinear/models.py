"""Core domain types.

All types are immutable frozen dataclasses. Mutations produce new instances via
:func:`dataclasses.replace`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

DIMENSION_NAMES: tuple[str, ...] = (
    "clarity",
    "context",
    "structure",
    "actionability",
    "efficiency",
    "grounding",
)
"""Canonical order of scoring dimensions used across the app."""

AnalyzerSource = Literal["heuristic", "llm", "llm-fallback-heuristic"]
"""Which code path produced an :class:`Analysis`.

``llm-fallback-heuristic`` indicates the LLM analyzer was configured but had to
fall back to the heuristic scorer (network error, schema failure, etc.).
"""


@dataclass(frozen=True, slots=True)
class Prompt:
    """A single prompt submitted for analysis."""

    content: str
    role: str = "user"
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def word_count(self) -> int:
        return len(self.content.split())

    @property
    def char_count(self) -> int:
        return len(self.content)

    def preview(self, max_length: int = 80) -> str:
        """Return a single-line summary for list views."""
        text = self.content.replace("\n", " ").strip()
        if len(text) <= max_length:
            return text
        return text[: max_length - 1].rstrip() + "…"


@dataclass(frozen=True, slots=True)
class DimensionScore:
    """One dimension's score plus a short human-readable rationale."""

    name: str
    value: float
    reason: str = ""

    def __post_init__(self) -> None:
        if self.name not in DIMENSION_NAMES:
            raise ValueError(f"Unknown dimension: {self.name!r}")
        if not 0.0 <= self.value <= 100.0:
            raise ValueError(f"Dimension {self.name} score out of range: {self.value}")


@dataclass(frozen=True, slots=True)
class TokenEstimate:
    """Token usage and (estimated) wasted cost for a single analysis."""

    input_tokens: int
    tokens_wasted: int
    dollars_wasted: float


@dataclass(frozen=True, slots=True)
class Analysis:
    """The full result of analyzing one prompt."""

    prompt: Prompt
    dimensions: tuple[DimensionScore, ...]
    overall: float
    letter: str
    tokens: TokenEstimate
    source: AnalyzerSource
    provider: str = "heuristic"
    model: str = ""
    warnings: tuple[str, ...] = ()

    def dimension(self, name: str) -> DimensionScore:
        for dim in self.dimensions:
            if dim.name == name:
                return dim
        raise KeyError(name)

    def as_dict(self) -> dict[str, float]:
        """Flat {name: value} view, useful for tabular display."""
        return {d.name: d.value for d in self.dimensions}

    def weakest(self) -> DimensionScore:
        return min(self.dimensions, key=lambda d: d.value)


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    """A persisted analysis record."""

    timestamp: datetime
    preview: str
    overall: float
    letter: str
    tokens_wasted: int
    dollars_wasted: float
    weakest: str
    provider: str
    model: str
    source: AnalyzerSource

    @classmethod
    def from_analysis(cls, analysis: Analysis) -> HistoryEntry:
        return cls(
            timestamp=analysis.prompt.submitted_at,
            preview=analysis.prompt.preview(),
            overall=analysis.overall,
            letter=analysis.letter,
            tokens_wasted=analysis.tokens.tokens_wasted,
            dollars_wasted=analysis.tokens.dollars_wasted,
            weakest=analysis.weakest().name,
            provider=analysis.provider,
            model=analysis.model,
            source=analysis.source,
        )
