"""LLM-backed analyzer with strict JSON schema and heuristic fallback."""

from __future__ import annotations

import json
from dataclasses import dataclass

from promptinear.analyzers.base import Analyzer
from promptinear.analyzers.heuristic import HeuristicAnalyzer
from promptinear.models import DIMENSION_NAMES, Analysis, DimensionScore, Prompt
from promptinear.providers.base import LLMProvider, ProviderError
from promptinear.scoring import curve_dimension, curve_grade, estimate_tokens, letter_grade

SYSTEM_PROMPT = """\
You are Promptinear, a strict rubric grader for prompts sent to AI coding assistants.

Score the user's prompt on six dimensions. Each dimension is a float from 0 to 100.

Rubric:
  clarity        - precise language, no hedging or ambiguity
  context        - describes current behavior, expected behavior, and relevant state
  structure      - uses numbered steps, bullets, or code fences for multi-part requests
  actionability  - starts with an explicit verb and names a concrete task
  efficiency     - minimal filler, every token carries information
  grounding      - references concrete artifacts: file paths, symbols, quoted errors

Output requirements:
  - Respond with a SINGLE JSON object. No prose, no markdown fencing, no commentary.
  - Schema (all fields required):
      {
        "clarity":       {"value": <0-100>, "reason": "<short phrase>"},
        "context":       {"value": <0-100>, "reason": "<short phrase>"},
        "structure":     {"value": <0-100>, "reason": "<short phrase>"},
        "actionability": {"value": <0-100>, "reason": "<short phrase>"},
        "efficiency":    {"value": <0-100>, "reason": "<short phrase>"},
        "grounding":     {"value": <0-100>, "reason": "<short phrase>"}
      }
  - Each "reason" must be one sentence, under 80 characters.
  - Do not include any other keys or values.
"""

USER_TEMPLATE = "Grade this prompt:\n\n---\n{prompt}\n---"


@dataclass(frozen=True, slots=True)
class _RawDimension:
    value: float
    reason: str


class LLMAnalyzer:
    """Analyzer that asks an :class:`LLMProvider` to score the prompt.

    On any provider error or schema failure, falls back to the heuristic
    analyzer and tags the result with ``source='llm-fallback-heuristic'``.
    """

    name = "llm"

    def __init__(self, provider: LLMProvider, fallback: Analyzer | None = None) -> None:
        self.provider = provider
        self.fallback = fallback or HeuristicAnalyzer()

    def analyze(self, prompt: Prompt) -> Analysis:
        user_message = USER_TEMPLATE.format(prompt=prompt.content)
        try:
            raw_response = self.provider.complete_json(
                system=SYSTEM_PROMPT,
                user=user_message,
            )
        except ProviderError as exc:
            return self._fallback(prompt, warning=f"{self.provider.name}: {exc}")

        dims_raw = _parse(raw_response)
        if dims_raw is None:
            return self._fallback(
                prompt,
                warning=f"{self.provider.name}: returned malformed JSON",
            )

        dims = tuple(
            DimensionScore(
                name=name,
                value=round(curve_dimension(dims_raw[name].value), 1),
                reason=dims_raw[name].reason,
            )
            for name in DIMENSION_NAMES
        )
        raw_overall = sum(dims_raw[name].value for name in DIMENSION_NAMES) / len(DIMENSION_NAMES)
        overall = curve_grade(raw_overall)

        return Analysis(
            prompt=prompt,
            dimensions=dims,
            overall=overall,
            letter=letter_grade(overall),
            tokens=estimate_tokens(prompt.content, overall),
            source="llm",
            provider=self.provider.name,
            model=self.provider.model,
        )

    def _fallback(self, prompt: Prompt, warning: str) -> Analysis:
        analysis = self.fallback.analyze(prompt)
        return Analysis(
            prompt=analysis.prompt,
            dimensions=analysis.dimensions,
            overall=analysis.overall,
            letter=analysis.letter,
            tokens=analysis.tokens,
            source="llm-fallback-heuristic",
            provider=self.provider.name,
            model=self.provider.model,
            warnings=(*analysis.warnings, warning),
        )


def _parse(raw: str) -> dict[str, _RawDimension] | None:
    """Parse the provider's JSON response into validated raw dimensions."""
    text = raw.strip()
    if not text:
        return None

    # Some providers occasionally wrap JSON in a markdown fence despite
    # instructions. Strip fences defensively.
    if text.startswith("```"):
        text = text.strip("`")
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    result: dict[str, _RawDimension] = {}
    for name in DIMENSION_NAMES:
        entry = data.get(name)
        if not isinstance(entry, dict):
            return None
        value = entry.get("value")
        reason = entry.get("reason", "")
        if not isinstance(value, (int, float)):
            return None
        if not isinstance(reason, str):
            return None
        if not 0 <= float(value) <= 100:
            return None
        result[name] = _RawDimension(value=float(value), reason=reason.strip()[:120])
    return result


__all__ = ["LLMAnalyzer"]
