from __future__ import annotations

import io
import json
from pathlib import Path

from promptinear import cli


def test_analyze_heuristic_json(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO("Fix the TypeError in data/parser.py in parse_line"),
    )
    rc = cli.main(
        [
            "--history-path",
            str(tmp_path / "h.json"),
            "analyze",
            "--stdin",
            "--format",
            "json",
            "--no-save",
            "--provider",
            "heuristic",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "dimensions" in data
    assert data["provider"] == "heuristic"


def test_analyze_rejects_empty_input(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    rc = cli.main(
        [
            "--history-path",
            str(tmp_path / "h.json"),
            "analyze",
            "--stdin",
            "--provider",
            "heuristic",
        ]
    )
    assert rc == 2


def test_history_empty(capsys, tmp_path: Path) -> None:
    rc = cli.main(
        [
            "--history-path",
            str(tmp_path / "empty.json"),
            "history",
            "--format",
            "json",
        ]
    )
    assert rc == 0
    assert capsys.readouterr().out.strip() == "[]"


def test_config_show_defaults(capsys, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("PROMPTINEAR_PROVIDER", raising=False)
    rc = cli.main(["--history-path", str(tmp_path / "h.json"), "config", "show"])
    assert rc == 0
    assert "provider" in capsys.readouterr().out


def test_config_set_invalid_provider(capsys, tmp_path: Path) -> None:
    rc = cli.main(
        [
            "--history-path",
            str(tmp_path / "h.json"),
            "config",
            "set",
            "provider",
            "bogus",
        ]
    )
    assert rc == 2


def test_analyze_with_broken_openai_endpoint(monkeypatch, tmp_path: Path, capsys) -> None:
    """--provider openai with a bad URL must fall back to heuristic inside LLMAnalyzer."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:1/v1")
    monkeypatch.setattr("sys.stdin", io.StringIO("Refactor parse_line in data/parser.py"))
    rc = cli.main(
        [
            "--history-path",
            str(tmp_path / "h.json"),
            "--provider",
            "openai",
            "--model",
            "gpt-4o-mini",
            "analyze",
            "--stdin",
            "--format",
            "json",
            "--no-save",
        ]
    )
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    # network will fail → analyzer falls back
    assert data["source"] in ("llm", "llm-fallback-heuristic")
