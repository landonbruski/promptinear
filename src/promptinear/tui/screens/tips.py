"""Usage tips / coaching content."""

from __future__ import annotations

from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt as RichPrompt
from rich.text import Text


@dataclass(frozen=True, slots=True)
class Tip:
    title: str
    dimensions: str
    guidance: str


TIPS: tuple[Tip, ...] = (
    Tip(
        "Control context churn",
        "Context, Efficiency, Structure",
        "Keep each chat focused on one bug or feature, then end it. Before switching tasks, "
        "write a short handoff note: goal, files touched, open questions, next command.",
    ),
    Tip(
        "Ask for one action",
        "Actionability, Clarity, Grounding",
        "Use an explicit verb and target: 'Refactor parse_line in data/parser.py to return "
        "(record, errors)'. If you need multiple changes, list them as numbered steps.",
    ),
    Tip(
        "Add concrete constraints",
        "Grounding, Structure",
        "State file paths, symbols, and limits up front: language level, style constraints, "
        "what must not change. Example: 'Use functions + while loops only; keep Analyze flow unchanged.'",
    ),
    Tip(
        "Compact before drift",
        "Efficiency, Context",
        "When replies start repeating or getting long, compact. Then continue with one fresh "
        "message that restates the current objective, acceptance checks, and next step.",
    ),
    Tip(
        "Hard reset when off track",
        "Context, Clarity",
        "If the chat is off-track, clear the session and restart with a tight brief: objective, "
        "current state, constraints, expected output format.",
    ),
    Tip(
        "Treat summaries as lossy",
        "Context, Clarity",
        "After any summary or compact, re-add critical facts explicitly: exact file names, edge "
        "cases, non-negotiable requirements. Never assume compressed context preserved every detail.",
    ),
    Tip(
        "Cache-aware turn timing",
        "Efficiency",
        "Reply within a few minutes when iterating so the provider's prompt cache is more likely "
        "to help. Keep boilerplate out of new turns; send only new facts and decisions.",
    ),
    Tip(
        "Close every turn with checks",
        "Structure, Actionability, Clarity",
        "End requests with clear validation: what command to run, what output should appear, "
        "what to do if it fails. This reduces rework loops and keeps fixes measurable.",
    ),
)


def run_tips(console: Console) -> None:
    if not TIPS:
        return

    index = 0
    while True:
        tip = TIPS[index]
        body = Text()
        body.append(f"Tip {index + 1} of {len(TIPS)}\n", style="bold cyan")
        body.append(f"Dimensions: {tip.dimensions}\n\n", style="dim")
        body.append(tip.guidance + "\n\n")
        body.append("Controls:  [n] next   [p] previous   [b] back", style="dim")

        console.print(
            Panel(body, title=tip.title, border_style="blue", padding=(1, 2))
        )

        action = RichPrompt.ask(
            Text("  Action", style="dim"),
            choices=["n", "p", "b"],
            default="b",
            show_choices=True,
        )
        if action == "n" and index < len(TIPS) - 1:
            index += 1
            console.print()
        elif action == "p" and index > 0:
            index -= 1
            console.print()
        elif action == "b":
            return
