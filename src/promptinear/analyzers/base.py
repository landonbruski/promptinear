"""Analyzer protocol."""

from __future__ import annotations

from typing import Protocol

from promptinear.models import Analysis, Prompt


class Analyzer(Protocol):
    """Scores a single prompt and always returns a valid :class:`Analysis`.

    LLM-backed analyzers fall back to the heuristic scorer on error and tag
    the result's ``source`` accordingly; they do not raise to the caller.
    """

    name: str

    def analyze(self, prompt: Prompt) -> Analysis: ...
