"""Help screen."""

from __future__ import annotations

from rich.console import Console

from promptinear.tui.widgets import help_panel


def run_help(console: Console) -> None:
    console.print(help_panel())
