"""Additional CLI subcommand coverage."""

from __future__ import annotations

import io
import json
from pathlib import Path

from promptinear import cli, storage
from promptinear.models import (
    DIMENSION_NAMES,
    Analysis,
    DimensionScore,
    Prompt,
    TokenEstimate,
)


def _seed_history(path: Path) -> None:
    dims = tuple(DimensionScore(name=n, value=70, reason="ok") for n in DIMENSION_NAMES)
    for overall in (60.0, 80.0, 90.0):
        analysis = Analysis(
            prompt=Prompt(content="demo"),
            dimensions=dims,
            overall=overall,
            letter="B",
            tokens=TokenEstimate(input_tokens=5, tokens_wasted=1, dollars_wasted=0.0),
            source="heuristic",
        )
        storage.append(path, analysis)


def test_history_pretty_output(capsys, tmp_path: Path) -> None:
    path = tmp_path / "h.json"
    _seed_history(path)
    rc = cli.main(["--history-path", str(path), "history", "--limit", "5"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "total" in out
    assert "heuristic" in out


def test_history_csv_output(capsys, tmp_path: Path) -> None:
    path = tmp_path / "h.json"
    _seed_history(path)
    rc = cli.main(["--history-path", str(path), "history", "--format", "csv"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("timestamp,letter")
    assert out.count("\n") >= 4


def test_dashboard_empty(capsys, tmp_path: Path) -> None:
    rc = cli.main(["--history-path", str(tmp_path / "none.json"), "dashboard"])
    assert rc == 0
    assert "empty" in capsys.readouterr().out.lower()


def test_dashboard_populated(capsys, tmp_path: Path) -> None:
    path = tmp_path / "h.json"
    _seed_history(path)
    rc = cli.main(["--history-path", str(path), "dashboard"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Grade distribution" in out
    assert "Weakest areas" in out


def test_config_path_command(capsys, tmp_path: Path) -> None:
    rc = cli.main(["--history-path", str(tmp_path / "h.json"), "config", "path"])
    assert rc == 0
    assert ".promptinear" in capsys.readouterr().out


def test_config_set_timeout_invalid(capsys, tmp_path: Path) -> None:
    rc = cli.main(
        ["--history-path", str(tmp_path / "h.json"), "config", "set", "timeout", "not-a-number"]
    )
    assert rc == 2


def test_analyze_markdown_output(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("Refactor parse_line in data/parser.py"))
    rc = cli.main(
        [
            "--history-path",
            str(tmp_path / "h.json"),
            "analyze",
            "--stdin",
            "--format",
            "markdown",
            "--no-save",
            "--provider",
            "heuristic",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("# Analysis")
    assert "| Dimension |" in out


def test_analyze_saves_to_history(monkeypatch, capsys, tmp_path: Path) -> None:
    path = tmp_path / "h.json"
    monkeypatch.setattr("sys.stdin", io.StringIO("Rename User to UserAccount across src/."))
    rc = cli.main(
        [
            "--history-path",
            str(path),
            "analyze",
            "--stdin",
            "--format",
            "json",
            "--provider",
            "heuristic",
        ]
    )
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["provider"] == "heuristic"
    assert path.exists()
    assert len(storage.load(path)) == 1


def test_config_set_provider_writes_file(tmp_path: Path, monkeypatch, capsys) -> None:
    fake_cfg = tmp_path / "p.toml"
    monkeypatch.setattr("promptinear.cli.CONFIG_FILE", fake_cfg)
    monkeypatch.setattr("promptinear.config.CONFIG_FILE", fake_cfg)
    rc = cli.main(
        ["--history-path", str(tmp_path / "h.json"), "config", "set", "provider", "heuristic"]
    )
    assert rc == 0
    assert "Saved" in capsys.readouterr().out
    assert fake_cfg.exists()


def test_analyze_missing_api_key_returns_error(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("sys.stdin", io.StringIO("Refactor parse_line"))
    rc = cli.main(
        [
            "--history-path",
            str(tmp_path / "h.json"),
            "--provider",
            "openai",
            "analyze",
            "--stdin",
            "--no-save",
        ]
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "API key" in err
