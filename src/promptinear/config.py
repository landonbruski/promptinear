"""Configuration resolution.

Precedence, highest first:

1. Explicit overrides passed by CLI flags
2. Environment variables
3. ``~/.promptinear/config.toml``
4. Built-in defaults

The config file is never written with secrets unless the user explicitly sets
one, and is chmod'd to 0600.
"""

from __future__ import annotations

import os
import stat
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib


CONFIG_DIR = Path.home() / ".promptinear"
CONFIG_FILE = CONFIG_DIR / "config.toml"

VALID_PROVIDERS = ("heuristic", "openai", "openai-compat", "anthropic", "gemini")
DEFAULT_MODELS: dict[str, str] = {
    "heuristic": "",
    "openai": "gpt-4o-mini",
    "openai-compat": "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5-20251001",
    "gemini": "gemini-2.5-flash",
}
ENV_KEY_BY_PROVIDER: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "openai-compat": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "heuristic": "",
}


@dataclass(frozen=True, slots=True)
class Config:
    """Resolved runtime configuration."""

    provider: str = "heuristic"
    model: str = ""
    api_key: str = ""
    base_url: str = ""
    timeout: float = 15.0
    history_path: Path = field(default_factory=lambda: Path.cwd() / "history.json")

    def with_overrides(self, **overrides: Any) -> Config:
        """Return a copy with non-None overrides applied."""
        clean = {k: v for k, v in overrides.items() if v is not None and v != ""}
        if not clean:
            return self
        return replace(self, **clean)

    def describe(self) -> dict[str, str]:
        """Return a redacted view of the config, safe to print."""
        return {
            "provider": self.provider,
            "model": self.model or DEFAULT_MODELS.get(self.provider, ""),
            "api_key": _redact(self.api_key),
            "base_url": self.base_url,
            "timeout": f"{self.timeout}s",
            "history_path": str(self.history_path),
        }

    def validate(self) -> list[str]:
        """Return a list of human-readable validation errors."""
        errors: list[str] = []
        if self.provider not in VALID_PROVIDERS:
            errors.append(
                f"Unknown provider {self.provider!r}. "
                f"Valid: {', '.join(VALID_PROVIDERS)}"
            )
        if self.timeout <= 0:
            errors.append("timeout must be positive")
        if self.provider != "heuristic" and not self._resolved_api_key():
            env_name = ENV_KEY_BY_PROVIDER.get(self.provider, "")
            errors.append(
                f"Provider {self.provider!r} needs an API key. "
                f"Set {env_name} or run `promptinear config set api_key <value>`."
            )
        return errors

    def _resolved_api_key(self) -> str:
        if self.api_key:
            return self.api_key
        env_name = ENV_KEY_BY_PROVIDER.get(self.provider, "")
        if env_name:
            return os.environ.get(env_name, "")
        return ""

    def resolved_api_key(self) -> str:
        """Return the API key, looking through env if not set directly."""
        return self._resolved_api_key()

    def resolved_model(self) -> str:
        return self.model or DEFAULT_MODELS.get(self.provider, "")


def _redact(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def load(config_path: Path | None = None) -> Config:
    """Load configuration from env + TOML file."""
    path = config_path or CONFIG_FILE
    cfg = Config()
    if path.is_file():
        cfg = _apply_toml(cfg, path)
    cfg = _apply_env(cfg)
    return cfg


def _apply_toml(cfg: Config, path: Path) -> Config:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"Failed to read {path}: {exc}") from exc
    updates: dict[str, Any] = {}
    for key in ("provider", "model", "api_key", "base_url"):
        if key in data:
            updates[key] = str(data[key])
    if "timeout" in data:
        updates["timeout"] = float(data["timeout"])
    if "history_path" in data:
        updates["history_path"] = Path(str(data["history_path"])).expanduser()
    return cfg.with_overrides(**updates)


def _apply_env(cfg: Config) -> Config:
    updates: dict[str, Any] = {}
    env = os.environ
    if "PROMPTINEAR_PROVIDER" in env:
        updates["provider"] = env["PROMPTINEAR_PROVIDER"]
    if "PROMPTINEAR_MODEL" in env:
        updates["model"] = env["PROMPTINEAR_MODEL"]
    if "PROMPTINEAR_TIMEOUT" in env:
        updates["timeout"] = float(env["PROMPTINEAR_TIMEOUT"])
    if "PROMPTINEAR_HISTORY_PATH" in env:
        updates["history_path"] = Path(env["PROMPTINEAR_HISTORY_PATH"]).expanduser()
    if "OPENAI_BASE_URL" in env:
        updates["base_url"] = env["OPENAI_BASE_URL"]
    return cfg.with_overrides(**updates)


def save(cfg: Config, config_path: Path | None = None) -> Path:
    """Persist ``cfg`` to TOML with 0600 permissions."""
    path = config_path or CONFIG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "# Promptinear configuration",
        "# Managed by `promptinear config set`.",
        "",
        f'provider = "{cfg.provider}"',
        f'model    = "{cfg.model}"',
        f'api_key  = "{cfg.api_key}"',
        f'base_url = "{cfg.base_url}"',
        f"timeout  = {cfg.timeout}",
        f'history_path = "{cfg.history_path}"',
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    return path


class ConfigError(RuntimeError):
    """Raised when configuration cannot be loaded or is invalid."""
