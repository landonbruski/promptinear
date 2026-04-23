"""Command-line entry point.

Subcommands:
    (no args)            launch the TUI
    analyze              analyze a single prompt (stdin or --text)
    history              print the last N history entries
    dashboard            print summary + distribution + weakest areas
    config show          print resolved configuration (secrets redacted)
    config set KEY VAL   update config.toml
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from promptinear import __version__, storage
from promptinear.analyzers import build_analyzer
from promptinear.config import (
    CONFIG_FILE,
    VALID_PROVIDERS,
    Config,
    ConfigError,
    load,
    save,
)
from promptinear.models import Analysis, HistoryEntry, Prompt
from promptinear.stats import grade_distribution, recent_overalls, summarize, weakest_counts


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    overrides: dict[str, object] = {}
    for key in ("provider", "model", "api_key", "base_url"):
        value = getattr(args, key, None)
        if value:
            overrides[key] = value
    history_path = getattr(args, "history_path", None)
    if history_path:
        overrides["history_path"] = Path(history_path)

    cfg = load().with_overrides(**overrides)

    handler = args.handler or _run_tui
    return handler(args, cfg)


def _global_flags() -> argparse.ArgumentParser:
    # NOTE: defaults are argparse.SUPPRESS so the same flag can appear on both
    # the main parser and the subcommand parser without subcommands overriding
    # values parsed at the top level with ``None``.
    parent = argparse.ArgumentParser(add_help=False)
    sup = argparse.SUPPRESS
    parent.add_argument("--provider", default=sup, help=f"Override provider ({'|'.join(VALID_PROVIDERS)})")
    parent.add_argument("--model", default=sup, help="Override model id")
    parent.add_argument("--api-key", dest="api_key", default=sup, help="Override API key for this run only")
    parent.add_argument("--base-url", dest="base_url", default=sup, help="Override base URL (OpenAI-compatible)")
    parent.add_argument("--history-path", dest="history_path", default=sup, help="Override history.json path")
    return parent


def _build_parser() -> argparse.ArgumentParser:
    globals_parent = _global_flags()
    parser = argparse.ArgumentParser(
        prog="promptinear",
        description="Bring-your-own-LLM prompt efficiency grader.",
        parents=[globals_parent],
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.set_defaults(handler=None)

    subs = parser.add_subparsers(dest="command")

    analyze = subs.add_parser(
        "analyze", parents=[globals_parent], help="Analyze a single prompt and exit"
    )
    analyze.add_argument("--text", help="Prompt text (or omit to read stdin)")
    analyze.add_argument("--stdin", action="store_true", help="Read prompt from stdin")
    analyze.add_argument(
        "--format",
        choices=("pretty", "json", "markdown"),
        default="pretty",
        help="Output format",
    )
    analyze.add_argument(
        "--no-save",
        dest="save",
        action="store_false",
        help="Do not append to history",
    )
    analyze.set_defaults(handler=_run_analyze, save=True)

    history = subs.add_parser(
        "history", parents=[globals_parent], help="Show recent analyses"
    )
    history.add_argument("--limit", type=int, default=10, help="Entries to show (default 10)")
    history.add_argument(
        "--format",
        choices=("pretty", "json", "csv"),
        default="pretty",
    )
    history.set_defaults(handler=_run_history)

    dash = subs.add_parser(
        "dashboard", parents=[globals_parent], help="Show aggregate stats"
    )
    dash.set_defaults(handler=_run_dashboard)

    cfg_cmd = subs.add_parser(
        "config", parents=[globals_parent], help="View or modify configuration"
    )
    cfg_subs = cfg_cmd.add_subparsers(dest="config_command")

    cfg_show = cfg_subs.add_parser("show", parents=[globals_parent], help="Print resolved configuration")
    cfg_show.set_defaults(handler=_run_config_show)

    cfg_set = cfg_subs.add_parser("set", parents=[globals_parent], help="Set a configuration key")
    cfg_set.add_argument("key", choices=("provider", "model", "api_key", "base_url", "timeout"))
    cfg_set.add_argument("value")
    cfg_set.set_defaults(handler=_run_config_set)

    cfg_path = cfg_subs.add_parser("path", parents=[globals_parent], help="Print the config file path")
    cfg_path.set_defaults(handler=_run_config_path)

    return parser


# ---------- handlers ----------


def _run_tui(_args: argparse.Namespace, cfg: Config) -> int:
    from promptinear.tui import run

    return run(cfg)


def _run_analyze(args: argparse.Namespace, cfg: Config) -> int:
    errors = cfg.validate()
    if errors:
        print("Configuration error:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 2

    text = _read_prompt(args)
    if not text.strip():
        print("No prompt supplied.", file=sys.stderr)
        return 2

    try:
        analyzer = build_analyzer(cfg)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    analysis = analyzer.analyze(Prompt(content=text))
    if args.save:
        storage.append(cfg.history_path, analysis)

    if args.format == "json":
        print(json.dumps(_analysis_to_dict(analysis), indent=2))
    elif args.format == "markdown":
        print(_analysis_to_markdown(analysis))
    else:
        _print_analysis(analysis)
    return 0


def _run_history(args: argparse.Namespace, cfg: Config) -> int:
    entries = storage.load(cfg.history_path)
    tail = entries[-args.limit :] if args.limit > 0 else entries

    if args.format == "json":
        print(json.dumps([_entry_to_dict(e) for e in tail], indent=2))
        return 0

    if args.format == "csv":
        print("timestamp,letter,overall,weakest,provider,preview")
        for entry in tail:
            preview = entry.preview.replace(",", " ").replace("\n", " ")
            print(
                f"{entry.timestamp.isoformat()},{entry.letter},"
                f"{entry.overall:.1f},{entry.weakest},{entry.provider},{preview}"
            )
        return 0

    if not tail:
        print("No history yet.")
        return 0

    summary = summarize(entries)
    print(
        f"{summary.total} total · avg {summary.average_letter} "
        f"({summary.average_overall:.1f}) · ${summary.total_dollars_wasted:.4f} wasted · "
        f"top weakness: {summary.top_weakness}\n"
    )
    for entry in tail:
        print(
            f"  {entry.timestamp.strftime('%Y-%m-%d %H:%M')}  "
            f"{entry.letter:>3}  {entry.overall:5.1f}  "
            f"{entry.weakest:<14} {entry.provider:<14} {entry.preview}"
        )
    return 0


def _run_dashboard(_args: argparse.Namespace, cfg: Config) -> int:
    entries = storage.load(cfg.history_path)
    if not entries:
        print("Dashboard is empty. Run `promptinear analyze` first.")
        return 0
    summary = summarize(entries)
    print(f"Total analyses:   {summary.total}")
    print(f"Average grade:    {summary.average_letter} ({summary.average_overall:.1f})")
    print(f"Tokens wasted:    {summary.total_tokens_wasted}")
    print(f"Dollars wasted:   ${summary.total_dollars_wasted:.4f}")
    print(f"Top weakness:     {summary.top_weakness} (×{summary.top_weakness_count})")
    print()
    print("Grade distribution:")
    for letter, count in grade_distribution(entries).items():
        print(f"  {letter}: {count}")
    print()
    print("Weakest areas:")
    for name, count in sorted(weakest_counts(entries).items(), key=lambda kv: -kv[1]):
        print(f"  {name.capitalize():14} {count}")
    print()
    recent = recent_overalls(entries, 12)
    if len(recent) >= 2:
        print("Recent overalls:  " + "  ".join(f"{v:.0f}" for v in recent))
    return 0


def _run_config_show(_args: argparse.Namespace, cfg: Config) -> int:
    for key, value in cfg.describe().items():
        print(f"  {key:14} {value}")
    print(f"\nConfig file: {CONFIG_FILE}")
    return 0


def _run_config_set(args: argparse.Namespace, cfg: Config) -> int:
    key = args.key
    value: object = args.value
    if key == "timeout":
        try:
            value = float(args.value)
        except ValueError:
            print("timeout must be a number", file=sys.stderr)
            return 2
    if key == "provider" and args.value not in VALID_PROVIDERS:
        print(
            f"provider must be one of: {', '.join(VALID_PROVIDERS)}",
            file=sys.stderr,
        )
        return 2
    updated = cfg.with_overrides(**{key: value})
    path = save(updated)
    print(f"Saved {key} → {path}")
    return 0


def _run_config_path(_args: argparse.Namespace, _cfg: Config) -> int:
    print(CONFIG_FILE)
    return 0


# ---------- helpers ----------


def _read_prompt(args: argparse.Namespace) -> str:
    text: str | None = args.text
    if text:
        return text
    if args.stdin or not sys.stdin.isatty():
        return sys.stdin.read()
    print("Paste a prompt, then press Ctrl-D on a blank line to submit:")
    return sys.stdin.read()


def _print_analysis(analysis: Analysis) -> None:
    print(
        f"Grade: {analysis.letter}  ({analysis.overall:.1f}/100)   "
        f"[{analysis.source} via {analysis.provider}]"
    )
    print("-" * 72)
    for dim in analysis.dimensions:
        print(f"  {dim.name.capitalize():14} {dim.value:5.1f}   {dim.reason}")
    print("-" * 72)
    print(
        f"  tokens={analysis.tokens.input_tokens}  "
        f"wasted={analysis.tokens.tokens_wasted}  "
        f"${analysis.tokens.dollars_wasted:.6f}"
    )
    if analysis.warnings:
        print("\nWarnings:")
        for w in analysis.warnings:
            print(f"  ! {w}")


def _analysis_to_markdown(analysis: Analysis) -> str:
    lines = [
        f"# Analysis: {analysis.letter} ({analysis.overall:.1f})",
        "",
        f"- Source: `{analysis.source}`",
        f"- Provider: `{analysis.provider}`",
        f"- Model: `{analysis.model or '-'}`",
        f"- Tokens (in/wasted): {analysis.tokens.input_tokens} / {analysis.tokens.tokens_wasted}",
        f"- Wasted cost: `${analysis.tokens.dollars_wasted:.6f}`",
        "",
        "| Dimension | Score | Rationale |",
        "| --- | ---:| --- |",
    ]
    for dim in analysis.dimensions:
        lines.append(f"| {dim.name.capitalize()} | {dim.value:.1f} | {dim.reason} |")
    if analysis.warnings:
        lines.append("")
        lines.append("**Warnings**")
        for w in analysis.warnings:
            lines.append(f"- {w}")
    return "\n".join(lines)


def _analysis_to_dict(analysis: Analysis) -> dict[str, object]:
    return {
        "letter": analysis.letter,
        "overall": analysis.overall,
        "source": analysis.source,
        "provider": analysis.provider,
        "model": analysis.model,
        "tokens": {
            "input": analysis.tokens.input_tokens,
            "wasted": analysis.tokens.tokens_wasted,
            "dollars": analysis.tokens.dollars_wasted,
        },
        "dimensions": [
            {"name": d.name, "value": d.value, "reason": d.reason}
            for d in analysis.dimensions
        ],
        "warnings": list(analysis.warnings),
    }


def _entry_to_dict(entry: HistoryEntry) -> dict[str, object]:
    from dataclasses import asdict

    data: dict[str, object] = asdict(entry)
    ts = data.get("timestamp")
    if isinstance(ts, datetime):
        data["timestamp"] = ts.isoformat()
    return data


if __name__ == "__main__":
    raise SystemExit(main())
