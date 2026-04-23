"""Analyzer implementations and factory."""

from __future__ import annotations

from promptinear.analyzers.base import Analyzer
from promptinear.analyzers.heuristic import HeuristicAnalyzer
from promptinear.analyzers.llm import LLMAnalyzer
from promptinear.config import Config
from promptinear.providers import build_provider


def build_analyzer(cfg: Config) -> Analyzer:
    """Return the appropriate analyzer for ``cfg``."""
    if cfg.provider == "heuristic":
        return HeuristicAnalyzer()
    provider = build_provider(cfg)
    return LLMAnalyzer(provider=provider, fallback=HeuristicAnalyzer())


__all__ = [
    "Analyzer",
    "HeuristicAnalyzer",
    "LLMAnalyzer",
    "build_analyzer",
]
