"""Welcome / landing screen."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from promptinear.models import HistoryEntry
from promptinear.stats import summarize


def run_welcome(console: Console, history: list[HistoryEntry], provider_label: str) -> None:
    body = Text()
    body.append("Promptinear scores your AI prompts and shows you where you're ", style="white")
    body.append("burning tokens.\n\n", style="bold red")

    body.append("How it works\n", style="bold cyan")
    body.append("  1. Paste a prompt (or pipe one with --stdin)\n")
    body.append("  2. Get scored on six dimensions with per-dimension reasoning\n")
    body.append("  3. Drill into weak areas for targeted coaching\n")
    body.append("  4. Track improvement over time in History and Dashboard\n\n")

    body.append("Current provider: ", style="bold cyan")
    body.append(provider_label + "\n\n", style="bold magenta")

    if history:
        summary = summarize(history)
        body.append(f"{summary.total}", style="bold cyan")
        body.append(" analyses saved.  Average grade: ", style="dim")
        body.append(summary.average_letter, style="bold cyan")
        body.append(f" ({summary.average_overall:.1f})", style="dim")
    else:
        body.append("No analyses yet - press [1] to begin.", style="bold green")

    console.print(Panel(body, title="Welcome", border_style="cyan", padding=(1, 2)))
