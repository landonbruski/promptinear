"""Provider for Anthropic's Messages API."""

from __future__ import annotations

import httpx

from promptinear.providers.base import ProviderError

DEFAULT_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


class AnthropicProvider:
    """Claude client via Messages API.

    Anthropic does not expose a strict JSON mode, so the analyzer's system
    prompt is responsible for producing clean JSON; the LLM analyzer validates
    the response and falls back to heuristic on any mismatch.
    """

    name = "anthropic"

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: float = 15.0,
        url: str = DEFAULT_URL,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self.model = model
        self._timeout = timeout
        self._url = url
        self._transport = transport

    def complete_json(self, system: str, user: str) -> str:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self._api_key,
            "anthropic-version": API_VERSION,
        }
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "temperature": 0,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }

        try:
            with httpx.Client(
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = client.post(self._url, headers=headers, json=payload)
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

        content = body.get("content")
        if not isinstance(content, list) or not content:
            raise ProviderError("response missing 'content'")

        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text")
                if isinstance(text, str) and text.strip():
                    return text

        raise ProviderError("response contained no text block")


def _truncate(text: str, limit: int = 240) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"
