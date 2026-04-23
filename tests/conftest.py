"""Shared pytest fixtures."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest


@pytest.fixture
def tmp_history(tmp_path: Path) -> Path:
    return tmp_path / "history.json"


@pytest.fixture
def mock_transport() -> Callable[[dict], httpx.MockTransport]:
    """Return a factory that produces a MockTransport returning ``body`` as JSON."""

    def factory(body: dict, *, status: int = 200) -> httpx.MockTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status, json=body)

        return httpx.MockTransport(handler)

    return factory


@pytest.fixture
def fail_transport() -> Callable[[int, str], httpx.MockTransport]:
    """Transport that always returns an HTTP error response."""

    def factory(status: int = 500, text: str = "boom") -> httpx.MockTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status, text=text)

        return httpx.MockTransport(handler)

    return factory


@pytest.fixture
def good_json_payload() -> str:
    return json.dumps(
        {
            "clarity":       {"value": 82.0, "reason": "precise"},
            "context":       {"value": 75.0, "reason": "adequate"},
            "structure":     {"value": 60.0, "reason": "single line"},
            "actionability": {"value": 88.0, "reason": "explicit verb"},
            "efficiency":    {"value": 70.0, "reason": "minor filler"},
            "grounding":     {"value": 90.0, "reason": "file path present"},
        }
    )
