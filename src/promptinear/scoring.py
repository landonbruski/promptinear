"""Grade curve, letter-grade mapping, and token-waste estimation.

The curve exists because raw heuristic scores clustered around the 60–75 range,
producing a long tail of Cs and Ds. The curve gently lifts mid-range scores so
the letter grades feel aligned with a user's intuition of prompt quality.

The waste model is intentionally rough: input-token count is estimated at four
characters per token (a common public figure), and the "wasted fraction" is
derived from the overall grade. A prompt graded 100 wastes 0 tokens; a prompt
graded 0 is assumed to cost twice the tokens it took to get a correct answer.
"""

from __future__ import annotations

from dataclasses import dataclass

from promptinear.models import TokenEstimate

LETTER_THRESHOLDS: tuple[tuple[float, str], ...] = (
    (97, "A+"),
    (93, "A"),
    (90, "A-"),
    (87, "B+"),
    (83, "B"),
    (80, "B-"),
    (77, "C+"),
    (73, "C"),
    (70, "C-"),
    (67, "D+"),
    (63, "D"),
    (60, "D-"),
    (0, "F"),
)

CHARS_PER_TOKEN = 4
"""Rough public figure for English text; used for token estimation only."""

DEFAULT_PRICE_PER_1K_TOKENS = 0.00015
"""Typical price for a small chat-completion model; used only for cost display."""


def letter_grade(score: float) -> str:
    """Return the letter grade for ``score`` (0–100)."""
    for threshold, letter in LETTER_THRESHOLDS:
        if score >= threshold:
            return letter
    return "F"


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    """Clamp ``value`` to ``[low, high]``."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def curve_grade(raw: float) -> float:
    """Apply the overall-grade curve.

    The curve is piecewise-linear with anchors chosen so that a raw 60 lifts to
    a strong C-, and a raw 90 maps cleanly to an A.
    """
    raw = clamp(raw)
    if raw <= 40:
        return round(raw * 1.0, 1)
    if raw <= 70:
        return round(40 + (raw - 40) * 1.1, 1)
    if raw <= 90:
        return round(73 + (raw - 70) * 1.0, 1)
    return round(93 + (raw - 90) * 0.7, 1)


def curve_dimension(raw: float) -> float:
    """Apply the per-dimension curve (a gentler lift than the overall curve)."""
    raw = clamp(raw)
    if raw <= 50:
        return round(raw * 1.05, 1)
    if raw <= 80:
        return round(52.5 + (raw - 50) * 1.05, 1)
    return round(84 + (raw - 80) * 0.8, 1)


def estimate_tokens(
    prompt_text: str,
    overall_grade: float,
    price_per_1k: float = DEFAULT_PRICE_PER_1K_TOKENS,
) -> TokenEstimate:
    """Estimate input tokens and the fraction that would have been "wasted".

    A higher grade means less waste. The model is:

    * ``input_tokens = len(prompt) / CHARS_PER_TOKEN``
    * ``waste_fraction = (100 - overall) / 100``
    * ``tokens_wasted = round(input_tokens * waste_fraction)``
    """
    input_tokens = max(1, len(prompt_text) // CHARS_PER_TOKEN)
    waste_fraction = max(0.0, (100.0 - overall_grade) / 100.0)
    tokens_wasted = round(input_tokens * waste_fraction)
    dollars_wasted = round((tokens_wasted / 1000.0) * price_per_1k, 6)
    return TokenEstimate(
        input_tokens=input_tokens,
        tokens_wasted=tokens_wasted,
        dollars_wasted=dollars_wasted,
    )


@dataclass(frozen=True, slots=True)
class DimensionMeta:
    """Static metadata for a dimension: coaching content."""

    name: str
    title: str
    why: str
    fix: str
    before: str
    after: str


DIMENSION_META: dict[str, DimensionMeta] = {
    "clarity": DimensionMeta(
        name="clarity",
        title="Clarity",
        why=(
            "Words like 'maybe', 'stuff', and 'things' force the model to guess your "
            "intent. When it guesses wrong, you burn tokens going back and forth."
        ),
        fix="Replace vague words with exact names, values, and descriptions.",
        before="maybe change some of the stuff in the config",
        after="Set max_retries to 3 in config.py",
    ),
    "context": DimensionMeta(
        name="context",
        title="Context",
        why=(
            "Without the current behavior and expected behavior, the model invents a "
            "problem to solve. Often the wrong one."
        ),
        fix="Describe what is happening, what you expected, and quote the error if any.",
        before="the login is broken",
        after="The login form returns a 500 because the session token is None",
    ),
    "structure": DimensionMeta(
        name="structure",
        title="Structure",
        why=(
            "Multi-part requests jammed into one sentence get mis-ordered or partially "
            "skipped."
        ),
        fix="Use numbered steps or bullet points. Put the most important item first.",
        before="update the API and also the tests and change the error messages",
        after="1. Add /api/users endpoint  2. Return 404 if not found  3. Add a test",
    ),
    "actionability": DimensionMeta(
        name="actionability",
        title="Actionability",
        why=(
            "Vague requests push the model to explore several approaches before "
            "settling on one - each abandoned approach is wasted output."
        ),
        fix="Start with a verb: fix, add, refactor, delete, rename. Say the exact action.",
        before="the button doesn't look right",
        after="Change the submit button background to #4f46e5 in style.css",
    ),
    "efficiency": DimensionMeta(
        name="efficiency",
        title="Efficiency",
        why=(
            "Every word in your prompt is an input token. Greetings and hedging add "
            "cost without adding signal."
        ),
        fix="Cut greetings and filler. Get to the task. You are not being rude - you are being efficient.",
        before="Hi! Could you please help me fix the login bug? Thanks!",
        after="Fix the login bug in auth.py: session expires after one request",
    ),
    "grounding": DimensionMeta(
        name="grounding",
        title="Grounding",
        why=(
            "Without concrete references like file paths, function names, or quoted "
            "errors, the model has to search the whole codebase to guess."
        ),
        fix="Include the exact file path, symbol name, line number, or error message.",
        before="fix the bug in the parser",
        after="Fix the TypeError in data/parser.py in parse_line",
    ),
}
