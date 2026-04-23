from __future__ import annotations

import json

from promptinear.analyzers.llm import LLMAnalyzer
from promptinear.models import Prompt
from promptinear.providers.base import LLMProvider, ProviderError


class _Stub:
    name = "stub"
    model = "stub-model"

    def __init__(self, response: str) -> None:
        self._response = response

    def complete_json(self, system: str, user: str) -> str:
        return self._response


class _Failing:
    name = "fails"
    model = "m"

    def complete_json(self, system: str, user: str) -> str:
        raise ProviderError("boom")


GOOD = json.dumps(
    {
        "clarity":       {"value": 85, "reason": "precise"},
        "context":       {"value": 75, "reason": "adequate"},
        "structure":     {"value": 60, "reason": "single line"},
        "actionability": {"value": 90, "reason": "verb up front"},
        "efficiency":    {"value": 70, "reason": "no filler"},
        "grounding":     {"value": 95, "reason": "file path present"},
    }
)


def test_llm_parses_strict_json() -> None:
    analyzer = LLMAnalyzer(provider=_Stub(GOOD))
    result = analyzer.analyze(Prompt(content="Fix data/x.py"))
    assert result.source == "llm"
    assert result.provider == "stub"
    assert result.letter
    assert all(d.reason for d in result.dimensions)


def test_llm_strips_markdown_fences() -> None:
    wrapped = "```json\n" + GOOD + "\n```"
    analyzer = LLMAnalyzer(provider=_Stub(wrapped))
    result = analyzer.analyze(Prompt(content="Fix data/x.py"))
    assert result.source == "llm"


def test_llm_falls_back_on_junk_json() -> None:
    analyzer = LLMAnalyzer(provider=_Stub("this is not json at all"))
    result = analyzer.analyze(Prompt(content="Fix data/x.py"))
    assert result.source == "llm-fallback-heuristic"
    assert result.warnings


def test_llm_falls_back_on_provider_error() -> None:
    analyzer = LLMAnalyzer(provider=_Failing())  # type: ignore[arg-type]
    result = analyzer.analyze(Prompt(content="Fix data/x.py"))
    assert result.source == "llm-fallback-heuristic"
    assert any("boom" in w for w in result.warnings)


def test_llm_rejects_out_of_range_value() -> None:
    bad = json.dumps(
        {
            "clarity":       {"value": 120, "reason": "x"},
            "context":       {"value": 70, "reason": "x"},
            "structure":     {"value": 70, "reason": "x"},
            "actionability": {"value": 70, "reason": "x"},
            "efficiency":    {"value": 70, "reason": "x"},
            "grounding":     {"value": 70, "reason": "x"},
        }
    )
    analyzer = LLMAnalyzer(provider=_Stub(bad))
    result = analyzer.analyze(Prompt(content="demo"))
    assert result.source == "llm-fallback-heuristic"


def test_provider_protocol_typecheck() -> None:
    stub: LLMProvider = _Stub(GOOD)  # type: ignore[assignment]
    assert stub.complete_json("a", "b")
