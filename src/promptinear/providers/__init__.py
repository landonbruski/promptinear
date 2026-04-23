"""LLM provider plugins."""

from __future__ import annotations

from promptinear.config import Config, ConfigError
from promptinear.providers.anthropic import AnthropicProvider
from promptinear.providers.base import LLMProvider, ProviderError
from promptinear.providers.gemini import GeminiProvider
from promptinear.providers.openai_compat import OpenAICompatProvider


def build_provider(cfg: Config) -> LLMProvider:
    """Factory: return the provider instance for ``cfg.provider``."""
    errors = cfg.validate()
    if errors:
        raise ConfigError("; ".join(errors))

    api_key = cfg.resolved_api_key()
    model = cfg.resolved_model()
    timeout = cfg.timeout
    base_url = cfg.base_url

    match cfg.provider:
        case "openai":
            return OpenAICompatProvider(
                api_key=api_key,
                model=model,
                base_url=base_url or "https://api.openai.com/v1",
                timeout=timeout,
                label="openai",
            )
        case "openai-compat":
            return OpenAICompatProvider(
                api_key=api_key,
                model=model,
                base_url=base_url or "http://localhost:11434/v1",
                timeout=timeout,
                label="openai-compat",
            )
        case "anthropic":
            return AnthropicProvider(api_key=api_key, model=model, timeout=timeout)
        case "gemini":
            return GeminiProvider(api_key=api_key, model=model, timeout=timeout)
        case _:
            raise ConfigError(f"Unknown provider: {cfg.provider!r}")


__all__ = [
    "AnthropicProvider",
    "GeminiProvider",
    "LLMProvider",
    "OpenAICompatProvider",
    "ProviderError",
    "build_provider",
]
