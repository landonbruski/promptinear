"""Smoke tests for TUI screens that don't require interactive input."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

from promptinear import storage
from promptinear.models import (
    DIMENSION_NAMES,
    Analysis,
    DimensionScore,
    HistoryEntry,
    Prompt,
    TokenEstimate,
)
from promptinear.tui.screens.dashboard import run_dashboard
from promptinear.tui.screens.help import run_help
from promptinear.tui.screens.welcome import run_welcome


def _console() -> Console:
    return Console(record=True, width=100, force_terminal=False)


def _entry() -> HistoryEntry:
    dims = tuple(DimensionScore(name=n, value=70, reason="") for n in DIMENSION_NAMES)
    analysis = Analysis(
        prompt=Prompt(content="demo"),
        dimensions=dims,
        overall=70.0,
        letter="C-",
        tokens=TokenEstimate(input_tokens=5, tokens_wasted=1, dollars_wasted=0.0),
        source="heuristic",
    )
    return HistoryEntry.from_analysis(analysis)


def test_welcome_empty_history() -> None:
    c = _console()
    run_welcome(c, [], "heuristic")
    out = c.export_text()
    assert "press [1]" in out


def test_welcome_with_history() -> None:
    c = _console()
    run_welcome(c, [_entry()], "openai:gpt-4o-mini")
    out = c.export_text()
    assert "analyses saved" in out
    assert "openai" in out


def test_help_screen() -> None:
    c = _console()
    run_help(c)
    assert "Main menu" in c.export_text()


def test_dashboard_empty() -> None:
    c = _console()
    run_dashboard(c, [])
    assert "empty" in c.export_text().lower()


def test_dashboard_populated() -> None:
    c = _console()
    run_dashboard(c, [_entry(), _entry()])
    out = c.export_text()
    assert "Grade distribution" in out
    assert "Weakest" in out


def test_storage_round_trip_through_screen(tmp_path: Path) -> None:
    """Dashboard reads what storage writes — smoke test the contract."""
    path = tmp_path / "h.json"
    dims = tuple(DimensionScore(name=n, value=85, reason="") for n in DIMENSION_NAMES)
    analysis = Analysis(
        prompt=Prompt(content="demo", submitted_at=datetime.now(timezone.utc)),
        dimensions=dims,
        overall=85.0,
        letter="B",
        tokens=TokenEstimate(input_tokens=3, tokens_wasted=0, dollars_wasted=0.0),
        source="heuristic",
    )
    storage.append(path, analysis)
    entries = storage.load(path)
    c = _console()
    run_dashboard(c, entries)
    assert "85" in c.export_text()
