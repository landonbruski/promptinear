"""Reusable Rich widgets composed into the TUI screens."""

from __future__ import annotations

from rich.align import Align
from rich.columns import Columns
from rich.console import Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from promptinear.models import Analysis, DimensionScore
from promptinear.scoring import DIMENSION_META
from promptinear.stats import HistorySummary
from promptinear.tui.theme import dimension_color, grade_style

BANNER = r"""
   ____                            _   _
  |  _ \ _ __ ___  _ __ ___  _ __ | |_(_)_ __   ___  __ _ _ __
  | |_) | '__/ _ \| '_ ` _ \| '_ \| __| | '_ \ / _ \/ _` | '__|
  |  __/| | | (_) | | | | | | |_) | |_| | | | |  __/ (_| | |
  |_|   |_|  \___/|_| |_| |_| .__/ \__|_|_| |_|\___|\__,_|_|
                            |_|"""

TAGLINE = "Prompt efficiency grader · Bring your own LLM · v2.0"


def banner(provider_label: str) -> Panel:
    body = Text()
    body.append(BANNER, style="cyan")
    body.append("\n\n  ", style="")
    body.append(TAGLINE, style="dim")
    body.append("\n  Provider: ", style="dim")
    body.append(provider_label, style="bold magenta")
    return Panel(body, border_style="cyan", padding=(0, 2))


def footer(provider_label: str, history_count: int) -> Panel:
    text = Text()
    text.append("│ ", style="dim")
    text.append(f"provider={provider_label}", style="bold magenta")
    text.append("  │  ", style="dim")
    text.append(f"history={history_count} entries", style="bold cyan")
    text.append("  │  ", style="dim")
    text.append("Ctrl+C to quit", style="dim")
    return Panel(Align.center(text), border_style="dim", padding=(0, 1))


def menu() -> Panel:
    table = Table.grid(padding=(0, 2), expand=True)
    table.add_column(justify="center", ratio=1)
    table.add_column(justify="center", ratio=1)
    table.add_column(justify="center", ratio=1)
    table.add_column(justify="center", ratio=1)
    table.add_column(justify="center", ratio=1)
    table.add_column(justify="center", ratio=1)

    def cell(key: str, label: str, color: str = "cyan") -> Text:
        t = Text()
        t.append(f"[{key}]", style=f"bold {color}")
        t.append(f" {label}", style="white")
        return t

    table.add_row(
        cell("1", "Analyze"),
        cell("2", "History"),
        cell("3", "Dashboard"),
        cell("4", "Tips"),
        cell("5", "Settings"),
        cell("H", "Help"),
    )
    return Panel(table, border_style="cyan", padding=(0, 1))


def grade_badge(letter: str) -> Text:
    badge = Text(f" {letter} ", style=grade_style(letter))
    return badge


def dimension_bars(analysis: Analysis, width: int = 34, fill_fraction: float = 1.0) -> Text:
    """Return a rich Text showing each dimension as a filled bar."""
    body = Text()
    for dim in analysis.dimensions:
        shown = round(dim.value * fill_fraction, 1)
        filled = int(width * shown / 100)
        bar = "█" * filled + "░" * (width - filled)
        color = dimension_color(dim.value)

        body.append(dim.name.capitalize().ljust(14), style="bold white")
        body.append(" ")
        body.append(bar, style=color)
        body.append(f" {shown:5.1f}\n", style=color)
    return body


def analysis_panel(analysis: Analysis, *, animated_fraction: float = 1.0) -> Panel:
    body = Group(
        dimension_bars(analysis, fill_fraction=animated_fraction),
    )
    title = Text()
    title.append("Prompt Score  ", style="bold white")
    title.append(grade_badge(analysis.letter))
    title.append(f"  {analysis.overall:.1f}/100", style="bold white")
    border = "green" if analysis.overall >= 80 else ("yellow" if analysis.overall >= 65 else "red")
    return Panel(body, title=title, border_style=border, padding=(1, 2))


def token_panel(analysis: Analysis) -> Panel:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold white")
    table.add_column(style="cyan")
    table.add_row("Input tokens (est)", f"{analysis.tokens.input_tokens}")
    table.add_row("Wasted tokens (est)", f"{analysis.tokens.tokens_wasted}")
    table.add_row("Wasted cost (est)", f"${analysis.tokens.dollars_wasted:.6f}")
    table.add_row("Analyzer", analysis.source)
    table.add_row("Provider", analysis.provider)
    if analysis.model:
        table.add_row("Model", analysis.model)
    if analysis.warnings:
        for w in analysis.warnings:
            table.add_row("Warning", w)
    return Panel(table, title="Token impact", border_style="cyan", padding=(1, 2))


def reasons_panel(analysis: Analysis) -> Panel:
    table = Table(show_header=True, header_style="bold cyan", border_style="cyan", expand=True)
    table.add_column("Dimension", style="bold white", no_wrap=True)
    table.add_column("Score", justify="right", width=7)
    table.add_column("Rationale")
    for dim in analysis.dimensions:
        score_text = Text(f"{dim.value:.1f}", style=dimension_color(dim.value))
        table.add_row(dim.name.capitalize(), score_text, dim.reason or "-")
    return Panel(table, title="Per-dimension rationale", border_style="cyan", padding=(1, 2))


def weak_panel(weak: list[DimensionScore]) -> Panel:
    body = Text()
    for i, dim in enumerate(weak, start=1):
        body.append(f" {i}. ", style="bold yellow")
        body.append(dim.name.capitalize(), style="bold white")
        body.append(f"  ({dim.value:.1f})\n", style=dimension_color(dim.value))
    body.append("\n Enter number(s) for coaching, or press Enter to skip.", style="dim")
    return Panel(body, title="Areas to improve", border_style="yellow", padding=(1, 2))


def coaching_panel(name: str, score: float, position: int, total: int) -> Panel:
    meta = DIMENSION_META.get(name)
    body = Text()
    if meta is None:
        body.append("No coaching tip for this dimension.\n", style="red")
        return Panel(body, title="Coaching", border_style="yellow", padding=(1, 2))

    body.append("Dimension: ", style="bold cyan")
    body.append(meta.title, style="bold white")
    body.append(f"   Score: {score:.1f}", style=dimension_color(score))
    body.append(f"   {position} of {total}\n\n", style="dim")

    body.append("Why this is weak\n", style="bold red")
    body.append(meta.why + "\n\n")

    body.append("How to fix it\n", style="bold green")
    body.append(meta.fix + "\n\n")

    body.append("Before\n", style="bold red")
    body.append(meta.before + "\n\n")

    body.append("After\n", style="bold green")
    body.append(meta.after + "\n\n")

    body.append("Controls:  [n] next   [p] previous   [b] back", style="dim")
    return Panel(body, title="Coaching", border_style="cyan", padding=(1, 2))


def history_summary_panel(summary: HistorySummary) -> Panel:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold white")
    table.add_column()
    table.add_row("Total analyses", f"[bold cyan]{summary.total}[/bold cyan]")
    table.add_row(
        "Average grade",
        f"[bold cyan]{summary.average_letter}[/bold cyan]  ({summary.average_overall:.1f})",
    )
    table.add_row(
        "Estimated waste",
        f"[bold cyan]${summary.total_dollars_wasted:.4f}[/bold cyan]  "
        f"({summary.total_tokens_wasted} tokens)",
    )
    table.add_row(
        "Top weakness",
        f"[bold yellow]{summary.top_weakness.capitalize()}[/bold yellow]"
        f"  ({summary.top_weakness_count})",
    )
    return Panel(table, title="History summary", border_style="magenta", padding=(1, 2))


def sparkline(values: list[float], width: int | None = None) -> Text:
    """Unicode block sparkline. Width defaults to ``len(values)``."""
    chars = "▁▂▃▄▅▆▇█"
    text = Text()
    if not values:
        return text
    lo = min(values)
    hi = max(values)
    spread = hi - lo or 1.0
    window = values if width is None or width >= len(values) else values[-width:]
    rendered = "".join(chars[min(7, max(0, int((v - lo) / spread * 7)))] for v in window)
    text.append(rendered, style="bold green")
    return text


def trend_panel(values: list[float]) -> Panel:
    if len(values) < 2:
        return Panel(
            Text("Need at least two analyses to show a trend.", style="dim"),
            title="Trend",
            border_style="green",
            padding=(1, 2),
        )
    body = Text()
    body.append(f"Last {len(values)} grades  ", style="bold cyan")
    body.append_text(sparkline(values))
    body.append(f"   avg={sum(values) / len(values):.1f}", style="dim")
    return Panel(body, title="Trend", border_style="green", padding=(1, 2))


def distribution_panel(counts: dict[str, int]) -> Panel:
    total = max(1, sum(counts.values()))
    body = Text()
    for letter in ("A", "B", "C", "D", "F"):
        count = counts.get(letter, 0)
        width = 30
        fill = int(width * count / total)
        bar = "█" * fill + "░" * (width - fill)
        body.append(f" {letter}  ", style="bold white")
        body.append(bar, style=_letter_color(letter))
        body.append(f"  {count}\n", style=_letter_color(letter))
    return Panel(body, title="Grade distribution", border_style="magenta", padding=(1, 2))


def weakest_panel(counts: dict[str, int]) -> Panel:
    if not counts:
        return Panel(
            Text("No analyses yet.", style="dim"),
            title="Weakest areas",
            border_style="cyan",
            padding=(1, 2),
        )
    total = max(1, sum(counts.values()))
    body = Text()
    for name, count in sorted(counts.items(), key=lambda kv: -kv[1]):
        width = 30
        fill = int(width * count / total)
        bar = "█" * fill + "░" * (width - fill)
        body.append(f" {name.capitalize():14}", style="bold white")
        body.append(bar, style="yellow")
        body.append(f"  {count}\n", style="yellow")
    return Panel(body, title="Weakest areas", border_style="cyan", padding=(1, 2))


def settings_panel(values: dict[str, str]) -> Panel:
    table = Table(show_header=False, box=None, padding=(0, 2), expand=True)
    table.add_column("Key", style="bold cyan", no_wrap=True)
    table.add_column("Value", style="white")
    for key in ("provider", "model", "api_key", "base_url", "timeout", "history_path"):
        table.add_row(key, values.get(key, ""))
    return Panel(table, title="Current configuration", border_style="magenta", padding=(1, 2))


def help_panel() -> Panel:
    body = Text()
    body.append("Main menu\n", style="bold cyan")
    body.append(" 1  Analyze a prompt\n")
    body.append(" 2  History\n")
    body.append(" 3  Dashboard\n")
    body.append(" 4  Coaching tips\n")
    body.append(" 5  Settings\n")
    body.append(" H  This help screen\n")
    body.append(" Q  Quit\n\n")

    body.append("Prompt entry\n", style="bold cyan")
    body.append(" - Paste one or more lines of prompt text.\n")
    body.append(" - Press Enter on an empty line to submit.\n\n")

    body.append("Coaching drill-down\n", style="bold cyan")
    body.append(" n  next weak area\n")
    body.append(" p  previous weak area\n")
    body.append(" b  back to menu\n\n")

    body.append("Quality checklist\n", style="bold cyan")
    body.append(" [ ] clear objective\n")
    body.append(" [ ] current state + expected state\n")
    body.append(" [ ] explicit output format\n")
    body.append(" [ ] constraints (language, libraries, style)\n")
    body.append(" [ ] success criteria\n")
    return Panel(body, title="Help", border_style="white", padding=(1, 2))


def rule_divider(label: str = "") -> Rule:
    return Rule(label, style="cyan")


def header_row(title: str, subtitle: str = "") -> Columns:
    left = Text(title, style="bold white")
    right = Text(subtitle, style="dim")
    return Columns([left, right], expand=True, align="left")


def _letter_color(letter: str) -> str:
    return {"A": "green", "B": "cyan", "C": "yellow", "D": "dark_orange3", "F": "red"}.get(
        letter, "white"
    )
