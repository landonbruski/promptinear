"""Color palette and style helpers."""

from __future__ import annotations

from rich.style import Style
from rich.theme import Theme

PALETTE = {
    "brand": "bold cyan",
    "brand.dim": "cyan",
    "success": "bold green",
    "warn": "bold yellow",
    "error": "bold red",
    "muted": "dim",
    "accent": "bold magenta",
    "border": "cyan",
    "panel.title": "bold white",
    "grade.a": "bold green",
    "grade.b": "bold cyan",
    "grade.c": "bold yellow",
    "grade.d": "bold orange3",
    "grade.f": "bold red",
    "kbd": "bold black on white",
}

THEME = Theme(PALETTE)


def grade_style(letter: str) -> Style:
    """Return a Style for a letter-grade badge."""
    head = (letter or "F")[0].upper()
    mapping = {
        "A": ("white", "green"),
        "B": ("black", "cyan"),
        "C": ("black", "yellow"),
        "D": ("white", "dark_orange3"),
        "F": ("white", "red"),
    }
    fg, bg = mapping.get(head, ("white", "red"))
    return Style(color=fg, bgcolor=bg, bold=True)


def dimension_color(score: float) -> str:
    if score >= 85:
        return "green"
    if score >= 70:
        return "cyan"
    if score >= 55:
        return "yellow"
    if score >= 40:
        return "dark_orange3"
    return "red"
