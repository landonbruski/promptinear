"""TUI main loop."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt as RichPrompt

from promptinear import storage
from promptinear.config import Config
from promptinear.tui.screens import (
    run_analyze,
    run_dashboard,
    run_help,
    run_history,
    run_settings,
    run_tips,
    run_welcome,
)
from promptinear.tui.theme import THEME
from promptinear.tui.widgets import banner, footer, menu


@dataclass
class AppState:
    cfg: Config
    history_path: Path
    screen: str = "welcome"


class App:
    def __init__(self, cfg: Config, console: Console | None = None) -> None:
        self.console = console or Console(theme=THEME)
        self.state = AppState(cfg=cfg, history_path=cfg.history_path)

    def run(self) -> int:
        try:
            self._loop()
        except KeyboardInterrupt:
            self.console.print("\n[bold cyan]Goodbye.[/bold cyan]")
        return 0

    def _loop(self) -> None:
        while True:
            self._render_frame()
            choice = self._prompt_choice()
            if choice in ("q", "quit"):
                self.console.clear()
                self.console.print("\n  [bold cyan]Goodbye.[/bold cyan]\n")
                return
            self._dispatch(choice)

    def _render_frame(self) -> None:
        self.console.clear()
        label = self._provider_label()
        history = storage.load(self.state.history_path)
        self.console.print(banner(label))
        self.console.print()

        screen = self.state.screen
        if screen == "analyze":
            run_analyze(self.console, self.state.cfg, self.state.history_path)
        elif screen == "history":
            run_history(self.console, self.state.history_path, history)
        elif screen == "dashboard":
            run_dashboard(self.console, history)
        elif screen == "tips":
            run_tips(self.console)
        elif screen == "settings":
            self.state.cfg = run_settings(self.console, self.state.cfg)
            self.state.history_path = self.state.cfg.history_path
        elif screen == "help":
            run_help(self.console)
        else:
            run_welcome(self.console, history, label)

        self.console.print()
        self.console.print(footer(label, len(history)))
        self.console.print()
        self.console.print(menu())
        self.console.print()

    def _prompt_choice(self) -> str:
        return RichPrompt.ask("  [bold cyan]›[/bold cyan]", default="", show_default=False).strip().lower()

    def _dispatch(self, choice: str) -> None:
        mapping = {
            "1": "analyze",
            "2": "history",
            "3": "dashboard",
            "4": "tips",
            "5": "settings",
            "h": "help",
            "": "welcome",
        }
        next_screen = mapping.get(choice)
        if next_screen:
            self.state.screen = next_screen

    def _provider_label(self) -> str:
        cfg = self.state.cfg
        model = cfg.resolved_model() or "-"
        return f"{cfg.provider}:{model}" if cfg.provider != "heuristic" else "heuristic"


def run(cfg: Config) -> int:
    return App(cfg).run()
