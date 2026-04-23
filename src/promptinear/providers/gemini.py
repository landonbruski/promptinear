"""Provider for Google Gemini's generateContent API."""

from __future__ import annotations

import httpx

from promptinear.providers.base import ProviderError

BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider:
    """Gemini client with ``response_mime_type=application/json``."""

    name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: float = 15.0,
        base: str = BASE,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self.model = model
        self._timeout = timeout
        self._base = base.rstrip("/")
        self._transport = transport

    def complete_json(self, system: str, user: str) -> str:
        url = f"{self._base}/{self.model}:generateContent?key={self._api_key}"
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": 0,
                "response_mime_type": "application/json",
            },
        }

        try:
            with httpx.Client(
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise ProviderError(f"network error: {exc}") from exc

        if response.status_code >= 400:
            raise ProviderError(
                f"HTTP {response.status_code}: {_truncate(response.text)}",
                status=response.status_code,
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise ProviderError("response was not valid JSON") from exc

        candidates = body.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise ProviderError("response missing 'candidates'")

        parts = (candidates[0].get("content") or {}).get("parts")
        if not isinstance(parts, list) or not parts:
            raise ProviderError("response missing content parts")

        text = parts[0].get("text")
        if not isinstance(text, str) or not text.strip():
            raise ProviderError("response missing text")
        return text


def _truncate(text: str, limit: int = 240) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"
