"""Aggregate statistics computed from history entries."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from promptinear.models import HistoryEntry
from promptinear.scoring import letter_grade


@dataclass(frozen=True, slots=True)
class HistorySummary:
    total: int
    average_overall: float
    average_letter: str
    total_dollars_wasted: float
    total_tokens_wasted: int
    top_weakness: str
    top_weakness_count: int


def summarize(entries: list[HistoryEntry]) -> HistorySummary:
    if not entries:
        return HistorySummary(
            total=0,
            average_overall=0.0,
            average_letter="N/A",
            total_dollars_wasted=0.0,
            total_tokens_wasted=0,
            top_weakness="-",
            top_weakness_count=0,
        )
    total = len(entries)
    avg = sum(e.overall for e in entries) / total
    dollars = round(sum(e.dollars_wasted for e in entries), 4)
    tokens = sum(e.tokens_wasted for e in entries)
    counts = Counter(e.weakest for e in entries)
    top_name, top_count = counts.most_common(1)[0]
    return HistorySummary(
        total=total,
        average_overall=round(avg, 1),
        average_letter=letter_grade(avg),
        total_dollars_wasted=dollars,
        total_tokens_wasted=tokens,
        top_weakness=top_name,
        top_weakness_count=top_count,
    )


def grade_distribution(entries: list[HistoryEntry]) -> dict[str, int]:
    """Return a count of how many entries fall into each letter-grade band."""
    buckets = ("A", "B", "C", "D", "F")
    counts: dict[str, int] = dict.fromkeys(buckets, 0)
    for entry in entries:
        head = entry.letter[0] if entry.letter else "F"
        if head in counts:
            counts[head] += 1
    return counts


def weakest_counts(entries: list[HistoryEntry]) -> dict[str, int]:
    return dict(Counter(e.weakest for e in entries))


def recent_overalls(entries: list[HistoryEntry], count: int) -> list[float]:
    """Return up to ``count`` most-recent overall scores, oldest to newest."""
    if count <= 0 or not entries:
        return []
    tail = entries[-count:]
    return [e.overall for e in tail]
