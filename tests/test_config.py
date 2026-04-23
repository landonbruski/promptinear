from __future__ import annotations

import os
import stat
from pathlib import Path

from promptinear import config as config_mod


def test_defaults_are_heuristic(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("PROMPTINEAR_PROVIDER", raising=False)
    cfg = config_mod.load(config_path=tmp_path / "nope.toml")
    assert cfg.provider == "heuristic"
    assert cfg.validate() == []


def test_env_overrides(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PROMPTINEAR_PROVIDER", "openai")
    monkeypatch.setenv("PROMPTINEAR_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    cfg = config_mod.load(config_path=tmp_path / "missing.toml")
    assert cfg.provider == "openai"
    assert cfg.resolved_model() == "gpt-4o-mini"
    assert cfg.resolved_api_key() == "sk-test"
    assert cfg.validate() == []


def test_validate_requires_api_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PROMPTINEAR_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = config_mod.load(config_path=tmp_path / "missing.toml")
    errors = cfg.validate()
    assert any("API key" in e for e in errors)


def test_describe_redacts_key() -> None:
    cfg = config_mod.Config(provider="openai", api_key="sk-abcdefghijklmnop")
    view = cfg.describe()
    assert "..." in view["api_key"]
    assert "abcdefg" not in view["api_key"]  # middle is not leaked
    short = config_mod.Config(provider="openai", api_key="short")
    assert short.describe()["api_key"] == "***"


def test_save_sets_permissions(tmp_path: Path) -> None:
    cfg = config_mod.Config(provider="heuristic")
    path = tmp_path / "pi-config.toml"
    config_mod.save(cfg, config_path=path)
    mode = stat.S_IMODE(os.stat(path).st_mode)
    assert mode == 0o600
    reloaded = config_mod.load(config_path=path)
    assert reloaded.provider == "heuristic"


def test_toml_file_provides_defaults(tmp_path: Path) -> None:
    path = tmp_path / "pi.toml"
    path.write_text(
        'provider = "anthropic"\nmodel = "claude-haiku-4-5-20251001"\napi_key = "sk-ant-x"\n',
        encoding="utf-8",
    )
    cfg = config_mod.load(config_path=path)
    assert cfg.provider == "anthropic"
    assert cfg.resolved_api_key() == "sk-ant-x"
