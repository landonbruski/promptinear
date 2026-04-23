"""Versioned history persistence.

Old (v1) history files - produced by the pre-2.0 single-file script - are
detected by the absence of a ``schema_version`` field and migrated in place to
v2 on first load. No data is lost.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from promptinear.models import Analysis, HistoryEntry

SCHEMA_VERSION = 2


def load(path: Path) -> list[HistoryEntry]:
    """Load and (if needed) migrate the history file at ``path``."""
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        backup = path.with_suffix(path.suffix + ".corrupt")
        path.rename(backup)
        return []

    if isinstance(data, list):
        entries = _migrate_v1(data)
        save(path, entries)
        return entries

    if isinstance(data, dict) and data.get("schema_version") == SCHEMA_VERSION:
        return [_from_dict(item) for item in data.get("entries", [])]

    # Unknown shape - preserve as corrupt and start fresh.
    backup = path.with_suffix(path.suffix + ".corrupt")
    path.rename(backup)
    return []


def save(path: Path, entries: list[HistoryEntry]) -> None:
    """Write ``entries`` to ``path`` atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "entries": [_to_dict(entry) for entry in entries],
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def append(path: Path, analysis: Analysis) -> list[HistoryEntry]:
    """Append an analysis to the history and return the full list."""
    entries = load(path)
    entries.append(HistoryEntry.from_analysis(analysis))
    save(path, entries)
    return entries


def clear(path: Path) -> None:
    """Remove all history but keep the file in place."""
    save(path, [])


def _to_dict(entry: HistoryEntry) -> dict[str, Any]:
    data = asdict(entry)
    data["timestamp"] = entry.timestamp.isoformat()
    return data


def _from_dict(data: dict[str, Any]) -> HistoryEntry:
    ts_raw = data.get("timestamp")
    ts = _parse_timestamp(ts_raw) if isinstance(ts_raw, str) else datetime.now(timezone.utc)
    return HistoryEntry(
        timestamp=ts,
        preview=str(data.get("preview", "")),
        overall=float(data.get("overall", 0.0)),
        letter=str(data.get("letter", "F")),
        tokens_wasted=int(data.get("tokens_wasted", 0)),
        dollars_wasted=float(data.get("dollars_wasted", 0.0)),
        weakest=str(data.get("weakest", "unknown")),
        provider=str(data.get("provider", "heuristic")),
        model=str(data.get("model", "")),
        source=str(data.get("source", "heuristic")),  # type: ignore[arg-type]
    )


def _parse_timestamp(value: str) -> datetime:
    """Parse ISO 8601 or legacy ``YYYY-MM-DD HH:MM`` formats."""
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.now(timezone.utc)


def _migrate_v1(records: list[Any]) -> list[HistoryEntry]:
    """Migrate legacy unversioned history records to ``HistoryEntry``."""
    migrated: list[HistoryEntry] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        ts_raw = record.get("timestamp")
        ts = _parse_timestamp(ts_raw) if isinstance(ts_raw, str) else datetime.now(timezone.utc)
        migrated.append(
            HistoryEntry(
                timestamp=ts,
                preview=str(record.get("preview", "")),
                overall=float(record.get("grade") or record.get("overall") or 0.0),
                letter=str(record.get("letter_grade", record.get("letter", "F"))),
                tokens_wasted=int(record.get("tokens_wasted", 0)),
                dollars_wasted=float(record.get("dollars_wasted", 0.0)),
                weakest=str(record.get("weakest", "unknown")),
                provider=str(record.get("provider", "heuristic")),
                model=str(record.get("model", "")),
                source="heuristic",
            )
        )
    return migrated
