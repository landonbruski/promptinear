"""Provider for OpenAI and any OpenAI-compatible endpoint.

Works with:
    - https://api.openai.com/v1              (OpenAI)
    - http://localhost:11434/v1              (Ollama)
    - http://localhost:1234/v1               (LM Studio)
    - https://openrouter.ai/api/v1           (OpenRouter)
    - http://localhost:8000/v1               (vLLM)
    - any other /v1/chat/completions-speaking backend
"""

from __future__ import annotations

import httpx

from promptinear.providers.base import ProviderError


class OpenAICompatProvider:
    """Chat-completions client with JSON-mode response format."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        timeout: float = 15.0,
        label: str = "openai",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self.model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self.name = label
        self._transport = transport

    def complete_json(self, system: str, user: str) -> str:
        url = f"{self._base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload: dict[str, object] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }

        try:
            with httpx.Client(
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = client.post(url, headers=headers, json=payload)
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

        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderError("response missing 'choices'")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ProviderError("response missing message.content")
        return content


def _truncate(text: str, limit: int = 240) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"
