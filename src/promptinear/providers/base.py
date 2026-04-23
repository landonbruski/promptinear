"""Shared provider contract."""

from __future__ import annotations

from typing import Protocol


class LLMProvider(Protocol):
    """Contract for a provider that returns a strict-JSON completion.

    Implementations must translate transport-level failures, HTTP errors, and
    vendor-specific error bodies into :class:`ProviderError` with a
    human-readable message. The analyzer never sees raw exceptions.
    """

    name: str
    model: str

    def complete_json(self, system: str, user: str) -> str: ...


class ProviderError(RuntimeError):
    """Raised by providers for any failure the caller should treat as non-fatal."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status
