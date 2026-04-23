"""Individual screen renderers."""

from __future__ import annotations

from promptinear.tui.screens.analyze import run_analyze
from promptinear.tui.screens.dashboard import run_dashboard
from promptinear.tui.screens.help import run_help
from promptinear.tui.screens.history import run_history
from promptinear.tui.screens.settings import run_settings
from promptinear.tui.screens.tips import run_tips
from promptinear.tui.screens.welcome import run_welcome

__all__ = [
    "run_analyze",
    "run_dashboard",
    "run_help",
    "run_history",
    "run_settings",
    "run_tips",
    "run_welcome",
]
