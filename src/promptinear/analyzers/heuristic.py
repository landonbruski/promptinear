"""Deterministic rule-based analyzer.

The heuristic does not call out to any network or LLM. It is intentionally fast
and predictable, and serves both as a standalone mode and as the fallback for
the LLM analyzer when a provider is unavailable or returns malformed data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from promptinear.models import (
    DIMENSION_NAMES,
    Analysis,
    DimensionScore,
    Prompt,
)
from promptinear.scoring import (
    clamp,
    curve_dimension,
    curve_grade,
    estimate_tokens,
    letter_grade,
)

FILLER_PHRASES: tuple[str, ...] = (
    "please",
    "thanks",
    "thank you",
    "could you",
    "would you mind",
    "i was wondering",
    "if you don't mind",
    "if possible",
    "maybe",
    "kinda",
    "sort of",
)

VAGUE_WORDS: tuple[str, ...] = (
    "stuff",
    "things",
    "something",
    "anything",
    "whatever",
    "somehow",
)

ACTION_VERBS: tuple[str, ...] = (
    "add",
    "fix",
    "refactor",
    "rename",
    "delete",
    "remove",
    "update",
    "create",
    "implement",
    "replace",
    "change",
    "move",
    "extract",
    "rewrite",
    "optimize",
    "migrate",
    "build",
    "generate",
    "return",
    "throw",
)

FILE_PATH_RE = re.compile(r"[\w./\-]+\.[A-Za-z]{1,6}(?::\d+)?")
CAMEL_OR_SNAKE_RE = re.compile(r"\b(?:[a-z_][a-z0-9_]{2,}|[A-Z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]*)\b")
QUOTED_ERROR_RE = re.compile(r'"[^"]{5,}"|\'[^\']{5,}\'')


@dataclass(frozen=True)
class HeuristicSignals:
    word_count: int
    line_count: int
    filler_hits: int
    vague_hits: int
    action_verb_hits: int
    has_file_path: bool
    has_code_fence: bool
    has_quoted: bool
    has_numbered_list: bool
    symbol_hits: int


class HeuristicAnalyzer:
    """Analyzer that uses simple text heuristics only."""

    name = "heuristic"

    def analyze(self, prompt: Prompt) -> Analysis:
        signals = _extract_signals(prompt.content)
        raw = _score_raw(signals)
        reasons = _explain(signals)

        dims = tuple(
            DimensionScore(
                name=name,
                value=round(curve_dimension(raw[name]), 1),
                reason=reasons[name],
            )
            for name in DIMENSION_NAMES
        )
        raw_overall = sum(raw[name] for name in DIMENSION_NAMES) / len(DIMENSION_NAMES)
        overall = curve_grade(raw_overall)
        tokens = estimate_tokens(prompt.content, overall)

        return Analysis(
            prompt=prompt,
            dimensions=dims,
            overall=overall,
            letter=letter_grade(overall),
            tokens=tokens,
            source="heuristic",
            provider="heuristic",
            model="",
        )


def _extract_signals(text: str) -> HeuristicSignals:
    lower = text.lower()
    words = text.split()
    word_count = len(words)
    line_count = len([line for line in text.splitlines() if line.strip()])
    filler_hits = sum(1 for phrase in FILLER_PHRASES if phrase in lower)
    vague_hits = sum(1 for word in VAGUE_WORDS if f" {word} " in f" {lower} ")
    action_verb_hits = sum(
        1 for verb in ACTION_VERBS if re.search(rf"\b{verb}\b", lower)
    )
    has_file_path = bool(FILE_PATH_RE.search(text))
    has_code_fence = "```" in text or text.count("`") >= 2
    has_quoted = bool(QUOTED_ERROR_RE.search(text))
    has_numbered_list = bool(re.search(r"(?m)^\s*\d+[.)]\s", text)) or bool(
        re.search(r"(?m)^\s*[-*]\s", text)
    )
    symbol_hits = len(CAMEL_OR_SNAKE_RE.findall(text))

    return HeuristicSignals(
        word_count=word_count,
        line_count=line_count,
        filler_hits=filler_hits,
        vague_hits=vague_hits,
        action_verb_hits=action_verb_hits,
        has_file_path=has_file_path,
        has_code_fence=has_code_fence,
        has_quoted=has_quoted,
        has_numbered_list=has_numbered_list,
        symbol_hits=symbol_hits,
    )


def _score_raw(s: HeuristicSignals) -> dict[str, float]:
    base = _length_base(s.word_count)

    clarity = base - 12 * s.vague_hits
    if s.word_count >= 15:
        clarity += 4

    context = base
    if s.word_count >= 30:
        context += 10
    if s.has_quoted:
        context += 10

    structure = base
    if s.has_numbered_list:
        structure += 15
    if s.has_code_fence:
        structure += 8
    if s.line_count >= 3:
        structure += 5

    actionability = base
    if s.action_verb_hits >= 1:
        actionability += 12
    if s.action_verb_hits >= 3:
        actionability += 6

    efficiency = 85 - s.filler_hits * 10
    if s.word_count > 180:
        efficiency -= 15
    if s.word_count < 5:
        efficiency -= 25

    grounding = 35
    if s.has_file_path:
        grounding += 30
    if s.has_code_fence:
        grounding += 15
    if s.symbol_hits >= 2:
        grounding += 10
    if s.has_quoted:
        grounding += 5

    return {
        "clarity": clamp(clarity),
        "context": clamp(context),
        "structure": clamp(structure),
        "actionability": clamp(actionability),
        "efficiency": clamp(efficiency),
        "grounding": clamp(grounding),
    }


def _length_base(word_count: int) -> float:
    if word_count < 5:
        return 30.0
    if word_count < 15:
        return 55.0
    if word_count < 60:
        return 72.0
    if word_count < 120:
        return 65.0
    return 50.0


def _explain(s: HeuristicSignals) -> dict[str, str]:
    reasons: dict[str, str] = {}

    if s.vague_hits:
        reasons["clarity"] = f"{s.vague_hits} vague word(s) detected."
    elif s.word_count < 10:
        reasons["clarity"] = "Prompt is too short to be clear."
    else:
        reasons["clarity"] = f"{s.word_count} words; no vague markers."

    if s.has_quoted:
        reasons["context"] = "Quoted error or state detected."
    elif s.word_count >= 30:
        reasons["context"] = "Adequate context length."
    else:
        reasons["context"] = "Short prompt; likely missing context."

    if s.has_numbered_list:
        reasons["structure"] = "Numbered or bulleted list present."
    elif s.has_code_fence:
        reasons["structure"] = "Code fence present."
    elif s.line_count >= 3:
        reasons["structure"] = f"Multi-line prompt ({s.line_count} lines)."
    else:
        reasons["structure"] = "Single line, no formatting."

    if s.action_verb_hits:
        reasons["actionability"] = f"{s.action_verb_hits} action verb(s)."
    else:
        reasons["actionability"] = "No explicit action verb."

    if s.filler_hits:
        reasons["efficiency"] = f"{s.filler_hits} filler phrase(s)."
    elif s.word_count > 180:
        reasons["efficiency"] = "Very long prompt; consider trimming."
    else:
        reasons["efficiency"] = "No filler phrases detected."

    grounding_bits: list[str] = []
    if s.has_file_path:
        grounding_bits.append("file path")
    if s.has_code_fence:
        grounding_bits.append("code fence")
    if s.symbol_hits >= 2:
        grounding_bits.append(f"{s.symbol_hits} identifier(s)")
    if grounding_bits:
        reasons["grounding"] = "Grounded by " + ", ".join(grounding_bits) + "."
    else:
        reasons["grounding"] = "No file path, code fence, or identifiers."

    return reasons


__all__ = ["HeuristicAnalyzer"]
