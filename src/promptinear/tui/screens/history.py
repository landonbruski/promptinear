"""History screen: summary + recent entries + trend."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt as RichPrompt
from rich.table import Table
from rich.text import Text

from promptinear import storage
from promptinear.models import HistoryEntry
from promptinear.stats import recent_overalls, summarize
from promptinear.tui.widgets import history_summary_panel, trend_panel


def run_history(console: Console, history_path: Path, history: list[HistoryEntry]) -> None:
    if not history:
        console.print(
            Panel(
                Text(
                    "No analyses saved yet. Run Analyze (1) to add your first prompt.",
                    style="yellow",
                ),
                title="History",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        return

    summary = summarize(history)
    console.print(history_summary_panel(summary))
    console.print()
    console.print(trend_panel(recent_overalls(history, 12)))
    console.print()

    table = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="cyan",
        expand=True,
        padding=(0, 1),
    )
    table.add_column("Time", no_wrap=True, style="dim")
    table.add_column("Letter", justify="center", width=6)
    table.add_column("Score", justify="right", width=7)
    table.add_column("Weakest", no_wrap=True)
    table.add_column("Provider", no_wrap=True, style="magenta")
    table.add_column("Preview", overflow="fold")
    for entry in list(history)[-12:][::-1]:
        table.add_row(
            entry.timestamp.strftime("%Y-%m-%d %H:%M"),
            entry.letter,
            f"{entry.overall:.1f}",
            entry.weakest.capitalize(),
            entry.provider,
            entry.preview,
        )
    console.print(Panel(table, title="Recent", border_style="cyan", padding=(0, 1)))
    console.print()

    action = RichPrompt.ask(
        Text("  Press C to clear history, or Enter to go back", style="dim"),
        default="",
        show_default=False,
    )
    if action.strip().lower() == "c":
        confirm = RichPrompt.ask(
            Text("  Type 'yes' to confirm history wipe", style="bold yellow"),
            default="no",
            show_default=False,
        )
        if confirm.strip().lower() == "yes":
            storage.clear(history_path)
            console.print("  [bold green]History cleared.[/bold green]")
