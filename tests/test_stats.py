from __future__ import annotations

from datetime import datetime, timezone

from promptinear.models import HistoryEntry
from promptinear.stats import (
    grade_distribution,
    recent_overalls,
    summarize,
    weakest_counts,
)


def _entry(overall: float, letter: str, weakest: str = "clarity") -> HistoryEntry:
    return HistoryEntry(
        timestamp=datetime.now(timezone.utc),
        preview="demo",
        overall=overall,
        letter=letter,
        tokens_wasted=5,
        dollars_wasted=0.001,
        weakest=weakest,
        provider="heuristic",
        model="",
        source="heuristic",
    )


def test_summarize_empty() -> None:
    s = summarize([])
    assert s.total == 0
    assert s.average_letter == "N/A"


def test_summarize_populated() -> None:
    entries = [_entry(90, "A-", "context"), _entry(70, "C-", "clarity"), _entry(70, "C-", "clarity")]
    s = summarize(entries)
    assert s.total == 3
    assert s.top_weakness == "clarity"
    assert s.top_weakness_count == 2


def test_grade_distribution() -> None:
    entries = [_entry(95, "A"), _entry(85, "B"), _entry(45, "F")]
    dist = grade_distribution(entries)
    assert dist["A"] == 1
    assert dist["F"] == 1
    assert dist["B"] == 1
    assert dist["C"] == 0


def test_weakest_counts() -> None:
    entries = [_entry(80, "B", "clarity"), _entry(80, "B", "grounding"), _entry(80, "B", "clarity")]
    counts = weakest_counts(entries)
    assert counts == {"clarity": 2, "grounding": 1}


def test_recent_overalls_limit() -> None:
    entries = [_entry(float(i), "C") for i in range(20)]
    recent = recent_overalls(entries, 5)
    assert recent == [15.0, 16.0, 17.0, 18.0, 19.0]
