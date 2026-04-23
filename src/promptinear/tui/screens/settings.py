"""Settings screen: view and edit configuration in place."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt as RichPrompt
from rich.text import Text

from promptinear import config as config_mod
from promptinear.config import VALID_PROVIDERS, Config
from promptinear.tui.widgets import settings_panel


def run_settings(console: Console, cfg: Config) -> Config:
    while True:
        console.print(settings_panel(cfg.describe()))
        console.print()
        body = Text()
        body.append("  [p] provider   ", style="bold cyan")
        body.append("[m] model   ", style="bold cyan")
        body.append("[k] api key   ", style="bold cyan")
        body.append("[u] base url   ", style="bold cyan")
        body.append("[t] timeout   ", style="bold cyan")
        body.append("[s] save   ", style="bold green")
        body.append("[b] back", style="bold white")
        console.print(body)
        console.print()

        action = RichPrompt.ask("  Action", default="b", show_default=False).strip().lower()

        if action == "p":
            provider = RichPrompt.ask(
                f"  Provider ({'|'.join(VALID_PROVIDERS)})", default=cfg.provider
            ).strip().lower()
            if provider in VALID_PROVIDERS:
                cfg = cfg.with_overrides(provider=provider)
        elif action == "m":
            model = RichPrompt.ask("  Model", default=cfg.model).strip()
            cfg = cfg.with_overrides(model=model)
        elif action == "k":
            api_key = RichPrompt.ask("  API key (leave blank to use env var)", default="").strip()
            if api_key:
                cfg = cfg.with_overrides(api_key=api_key)
        elif action == "u":
            base_url = RichPrompt.ask("  Base URL (OpenAI-compatible)", default=cfg.base_url).strip()
            cfg = cfg.with_overrides(base_url=base_url)
        elif action == "t":
            raw = RichPrompt.ask("  Timeout seconds", default=str(cfg.timeout)).strip()
            if raw.replace(".", "", 1).isdigit():
                cfg = cfg.with_overrides(timeout=float(raw))
        elif action == "s":
            path = config_mod.save(cfg)
            console.print(
                Panel(
                    Text(f"Saved to {path}", style="bold green"),
                    border_style="green",
                    padding=(0, 2),
                )
            )
            return cfg
        elif action == "b":
            return cfg
