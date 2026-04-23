from __future__ import annotations

import pytest

from promptinear.models import (
    DIMENSION_NAMES,
    Analysis,
    DimensionScore,
    HistoryEntry,
    Prompt,
    TokenEstimate,
)


def test_prompt_word_and_preview() -> None:
    p = Prompt(content="fix the bug in auth.py\n\nlooks urgent")
    assert p.word_count == 7
    assert p.preview(10).endswith("…")
    assert p.preview(100) == "fix the bug in auth.py  looks urgent"


def test_dimension_score_validation() -> None:
    with pytest.raises(ValueError):
        DimensionScore(name="nope", value=50)
    with pytest.raises(ValueError):
        DimensionScore(name="clarity", value=101)


def _make_analysis(values: dict[str, float]) -> Analysis:
    dims = tuple(DimensionScore(name=n, value=values[n], reason="") for n in DIMENSION_NAMES)
    overall = sum(values.values()) / len(values)
    return Analysis(
        prompt=Prompt(content="demo prompt text"),
        dimensions=dims,
        overall=overall,
        letter="B",
        tokens=TokenEstimate(input_tokens=10, tokens_wasted=3, dollars_wasted=0.0),
        source="heuristic",
    )


def test_analysis_weakest_and_asdict() -> None:
    values = {n: 80.0 for n in DIMENSION_NAMES}
    values["efficiency"] = 40.0
    analysis = _make_analysis(values)
    assert analysis.weakest().name == "efficiency"
    assert analysis.as_dict()["efficiency"] == 40.0


def test_history_entry_round_trip() -> None:
    values = {n: 70.0 for n in DIMENSION_NAMES}
    analysis = _make_analysis(values)
    entry = HistoryEntry.from_analysis(analysis)
    assert entry.letter == "B"
    assert entry.weakest in DIMENSION_NAMES
    assert entry.source == "heuristic"
