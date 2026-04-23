from __future__ import annotations

import json
from pathlib import Path

from promptinear import storage
from promptinear.models import (
    DIMENSION_NAMES,
    Analysis,
    DimensionScore,
    HistoryEntry,
    Prompt,
    TokenEstimate,
)


def _make_entry(overall: float = 72.0) -> HistoryEntry:
    dims = tuple(DimensionScore(name=n, value=overall, reason="") for n in DIMENSION_NAMES)
    analysis = Analysis(
        prompt=Prompt(content="hello"),
        dimensions=dims,
        overall=overall,
        letter="C",
        tokens=TokenEstimate(input_tokens=1, tokens_wasted=0, dollars_wasted=0.0),
        source="heuristic",
    )
    return HistoryEntry.from_analysis(analysis)


def test_load_missing_file(tmp_path: Path) -> None:
    assert storage.load(tmp_path / "missing.json") == []


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "hist.json"
    storage.save(path, [_make_entry(), _make_entry(50.0)])
    loaded = storage.load(path)
    assert len(loaded) == 2
    assert loaded[1].overall == 50.0


def test_migrate_v1_list(tmp_path: Path) -> None:
    path = tmp_path / "hist.json"
    legacy = [
        {
            "timestamp": "2026-04-01 12:00",
            "preview": "legacy one",
            "grade": 82.0,
            "letter_grade": "B",
            "tokens_wasted": 4,
            "dollars_wasted": 0.0001,
            "weakest": "clarity",
        }
    ]
    path.write_text(json.dumps(legacy), encoding="utf-8")
    entries = storage.load(path)
    assert len(entries) == 1
    assert entries[0].preview == "legacy one"
    assert entries[0].source == "heuristic"
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["schema_version"] == 2


def test_corrupt_file_is_moved_aside(tmp_path: Path) -> None:
    path = tmp_path / "hist.json"
    path.write_text("this is not json", encoding="utf-8")
    assert storage.load(path) == []
    assert (tmp_path / "hist.json.corrupt").exists()


def test_append_and_clear(tmp_path: Path) -> None:
    path = tmp_path / "hist.json"
    entry = _make_entry()
    dims = tuple(DimensionScore(name=n, value=80, reason="") for n in DIMENSION_NAMES)
    analysis = Analysis(
        prompt=Prompt(content="demo"),
        dimensions=dims,
        overall=80.0,
        letter="B-",
        tokens=TokenEstimate(input_tokens=1, tokens_wasted=0, dollars_wasted=0.0),
        source="heuristic",
    )
    storage.save(path, [entry])
    storage.append(path, analysis)
    assert len(storage.load(path)) == 2
    storage.clear(path)
    assert storage.load(path) == []
