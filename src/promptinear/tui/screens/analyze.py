"""Analyze screen: read a prompt, score it, coach the user."""

from __future__ import annotations

import time
from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Prompt as RichPrompt
from rich.text import Text

from promptinear import storage
from promptinear.analyzers import build_analyzer
from promptinear.config import Config
from promptinear.models import Analysis, DimensionScore, Prompt
from promptinear.tui.widgets import (
    analysis_panel,
    coaching_panel,
    reasons_panel,
    token_panel,
    weak_panel,
)

WEAK_THRESHOLD = 70.0


def run_analyze(console: Console, cfg: Config, history_path: Path) -> Analysis | None:
    prompt_text = _read_prompt(console)
    if not prompt_text:
        return None

    analyzer = build_analyzer(cfg)
    with console.status("[bold cyan]Scoring…[/bold cyan]", spinner="dots"):
        analysis = analyzer.analyze(Prompt(content=prompt_text))

    _animate_bars(console, analysis)
    console.print()
    console.print(token_panel(analysis))
    console.print()
    console.print(reasons_panel(analysis))

    weak = [d for d in analysis.dimensions if d.value < WEAK_THRESHOLD]
    if weak:
        console.print()
        console.print(weak_panel(weak))
        _coaching_loop(console, weak)
    else:
        console.print()
        console.print(
            Panel(
                Text("All dimensions are strong. Ship it.", style="bold green"),
                border_style="green",
                padding=(1, 2),
            )
        )

    storage.append(history_path, analysis)
    return analysis


def _read_prompt(console: Console) -> str:
    console.print(
        Panel(
            Text(
                "Paste a prompt below, then press Enter on an empty line to submit.",
                style="white",
            ),
            title="Analyze",
            border_style="green",
            padding=(1, 2),
        )
    )
    console.print()
    lines: list[str] = []
    while True:
        marker = "  > " if not lines else "    "
        line = input(marker)
        if line.strip() == "" and lines:
            break
        if line.strip() == "" and not lines:
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _animate_bars(console: Console, analysis: Analysis) -> None:
    steps = 10
    with Live(console=console, refresh_per_second=24, transient=False) as live:
        for step in range(steps + 1):
            fraction = step / steps
            live.update(analysis_panel(analysis, animated_fraction=fraction))
            if step < steps:
                time.sleep(0.03)


def _coaching_loop(console: Console, weak: list[DimensionScore]) -> None:
    raw = RichPrompt.ask(
        Text("  Enter weak-area numbers (e.g. 1 3) or press Enter to skip", style="dim"),
        default="",
        show_default=False,
    )
    chosen = _parse_selection(raw, len(weak))
    if not chosen:
        return

    selected = [weak[i - 1] for i in chosen]
    index = 0
    while True:
        dim = selected[index]
        console.print()
        console.print(coaching_panel(dim.name, dim.value, index + 1, len(selected)))
        action = RichPrompt.ask(
            Text("  Action", style="dim"),
            choices=["n", "p", "b"],
            default="b",
            show_choices=True,
        )
        if action == "n" and index < len(selected) - 1:
            index += 1
        elif action == "p" and index > 0:
            index -= 1
        elif action == "b":
            return


def _parse_selection(raw: str, upper: int) -> list[int]:
    picked: list[int] = []
    for token in raw.replace(",", " ").split():
        if token.isdigit():
            idx = int(token)
            if 1 <= idx <= upper and idx not in picked:
                picked.append(idx)
    return picked
