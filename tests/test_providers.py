from __future__ import annotations

import httpx
import pytest

from promptinear.providers.anthropic import AnthropicProvider
from promptinear.providers.base import ProviderError
from promptinear.providers.gemini import GeminiProvider
from promptinear.providers.openai_compat import OpenAICompatProvider


def _transport(body: dict, *, status: int = 200) -> httpx.MockTransport:
    return httpx.MockTransport(lambda _request: httpx.Response(status, json=body))


def _error_transport(status: int = 500) -> httpx.MockTransport:
    return httpx.MockTransport(lambda _request: httpx.Response(status, text="boom"))


def test_openai_compat_success() -> None:
    body = {
        "choices": [
            {"message": {"content": '{"ok": true}', "role": "assistant"}}
        ]
    }
    provider = OpenAICompatProvider(
        api_key="sk", model="gpt-4o-mini", base_url="https://api.openai.com/v1",
        transport=_transport(body),
    )
    assert provider.complete_json("sys", "user") == '{"ok": true}'


def test_openai_compat_http_error() -> None:
    provider = OpenAICompatProvider(
        api_key="sk", model="gpt-4o-mini", base_url="https://x",
        transport=_error_transport(503),
    )
    with pytest.raises(ProviderError) as exc:
        provider.complete_json("sys", "user")
    assert exc.value.status == 503


def test_openai_compat_missing_content() -> None:
    provider = OpenAICompatProvider(
        api_key="sk", model="m", base_url="https://x",
        transport=_transport({"choices": [{"message": {}}]}),
    )
    with pytest.raises(ProviderError):
        provider.complete_json("sys", "user")


def test_anthropic_success() -> None:
    body = {"content": [{"type": "text", "text": '{"ok": true}'}]}
    provider = AnthropicProvider(api_key="sk-ant", model="claude", transport=_transport(body))
    assert '"ok"' in provider.complete_json("s", "u")


def test_anthropic_no_text_block() -> None:
    body = {"content": [{"type": "tool_use"}]}
    provider = AnthropicProvider(api_key="sk-ant", model="claude", transport=_transport(body))
    with pytest.raises(ProviderError):
        provider.complete_json("s", "u")


def test_gemini_success() -> None:
    body = {"candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}]}
    provider = GeminiProvider(api_key="g", model="gemini-2.5-flash", transport=_transport(body))
    assert '"ok"' in provider.complete_json("s", "u")


def test_gemini_missing_candidates() -> None:
    provider = GeminiProvider(api_key="g", model="m", transport=_transport({"candidates": []}))
    with pytest.raises(ProviderError):
        provider.complete_json("s", "u")
