"""Smoke tests for Rich widgets - render into a recorded console."""

from __future__ import annotations

from datetime import datetime, timezone

from rich.console import Console

from promptinear.models import (
    DIMENSION_NAMES,
    Analysis,
    DimensionScore,
    HistoryEntry,
    Prompt,
    TokenEstimate,
)
from promptinear.stats import grade_distribution, summarize, weakest_counts
from promptinear.tui import widgets


def _sample_analysis() -> Analysis:
    dims = tuple(
        DimensionScore(name=name, value=60 + i * 5, reason=f"reason {name}")
        for i, name in enumerate(DIMENSION_NAMES)
    )
    return Analysis(
        prompt=Prompt(content="Fix data/parser.py"),
        dimensions=dims,
        overall=72.0,
        letter="C",
        tokens=TokenEstimate(input_tokens=12, tokens_wasted=3, dollars_wasted=0.0),
        source="heuristic",
        provider="heuristic",
        model="",
    )


def _sample_entry(overall: float = 80.0, weakest: str = "clarity") -> HistoryEntry:
    return HistoryEntry(
        timestamp=datetime.now(timezone.utc),
        preview="demo",
        overall=overall,
        letter="B",
        tokens_wasted=1,
        dollars_wasted=0.001,
        weakest=weakest,
        provider="heuristic",
        model="",
        source="heuristic",
    )


def _render(renderable) -> str:
    console = Console(record=True, width=100)
    console.print(renderable)
    return console.export_text()


def test_banner_renders() -> None:
    assert "Prompt" in _render(widgets.banner("heuristic"))


def test_menu_renders() -> None:
    text = _render(widgets.menu())
    assert "Analyze" in text
    assert "Help" in text


def test_analysis_panel_contains_scores() -> None:
    text = _render(widgets.analysis_panel(_sample_analysis()))
    assert "Clarity" in text
    assert "/100" in text


def test_reasons_panel() -> None:
    text = _render(widgets.reasons_panel(_sample_analysis()))
    assert "Dimension" in text
    assert "reason clarity" in text


def test_token_panel_shows_fields() -> None:
    text = _render(widgets.token_panel(_sample_analysis()))
    assert "Input tokens" in text
    assert "Provider" in text


def test_weak_panel_lists_entries() -> None:
    weak = [_sample_analysis().dimensions[0]]
    text = _render(widgets.weak_panel(weak))
    assert "Areas to improve" in text


def test_coaching_panel() -> None:
    text = _render(widgets.coaching_panel("clarity", 55.0, 1, 2))
    assert "Why this is weak" in text


def test_history_summary_panel() -> None:
    entries = [_sample_entry(80, "clarity"), _sample_entry(70, "efficiency")]
    text = _render(widgets.history_summary_panel(summarize(entries)))
    assert "Total analyses" in text


def test_distribution_and_weakest() -> None:
    entries = [_sample_entry(95, "clarity"), _sample_entry(70, "structure")]
    dist_text = _render(widgets.distribution_panel(grade_distribution(entries)))
    assert "Grade distribution" in dist_text
    weak_text = _render(widgets.weakest_panel(weakest_counts(entries)))
    assert "Weakest" in weak_text


def test_trend_and_sparkline() -> None:
    text = _render(widgets.trend_panel([50.0, 60.0, 70.0, 80.0]))
    assert "Trend" in text
    short_text = _render(widgets.trend_panel([80.0]))
    assert "at least two" in short_text


def test_settings_panel() -> None:
    values = {
        "provider": "heuristic",
        "model": "",
        "api_key": "***",
        "base_url": "",
        "timeout": "15s",
        "history_path": "/tmp/h.json",
    }
    text = _render(widgets.settings_panel(values))
    assert "provider" in text


def test_help_panel() -> None:
    text = _render(widgets.help_panel())
    assert "Main menu" in text
