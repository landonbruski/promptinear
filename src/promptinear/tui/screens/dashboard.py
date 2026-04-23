"""Dashboard screen: distribution + weakest areas + trend."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from promptinear.models import HistoryEntry
from promptinear.stats import (
    grade_distribution,
    recent_overalls,
    summarize,
    weakest_counts,
)
from promptinear.tui.widgets import (
    distribution_panel,
    history_summary_panel,
    trend_panel,
    weakest_panel,
)


def run_dashboard(console: Console, history: list[HistoryEntry]) -> None:
    if not history:
        console.print(
            Panel(
                Text(
                    "Dashboard is empty. Analyze a few prompts to populate it.",
                    style="yellow",
                ),
                title="Dashboard",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        return

    summary = summarize(history)
    console.print(history_summary_panel(summary))
    console.print()
    console.print(distribution_panel(grade_distribution(history)))
    console.print()
    console.print(weakest_panel(weakest_counts(history)))
    console.print()
    console.print(trend_panel(recent_overalls(history, 24)))
