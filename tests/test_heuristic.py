from __future__ import annotations

from promptinear.analyzers.heuristic import HeuristicAnalyzer
from promptinear.models import Prompt


def test_short_prompt_scores_low() -> None:
    analysis = HeuristicAnalyzer().analyze(Prompt(content="fix it"))
    assert analysis.overall < 60


def test_grounded_prompt_scores_well() -> None:
    prompt = Prompt(
        content=(
            "1. Fix the TypeError in data/parser.py in the parse_line function.\n"
            "2. When input is an empty string it currently crashes.\n"
            "3. Return an empty list instead."
        )
    )
    analysis = HeuristicAnalyzer().analyze(prompt)
    assert analysis.overall >= 70
    grounding = analysis.dimension("grounding")
    assert grounding.value >= 70
    structure = analysis.dimension("structure")
    assert structure.value >= 65


def test_filler_drops_efficiency() -> None:
    prompt = Prompt(
        content=(
            "Hi, could you please maybe help me if you don't mind? "
            "I was wondering if you could kinda look at the thing."
        )
    )
    analysis = HeuristicAnalyzer().analyze(prompt)
    efficiency = analysis.dimension("efficiency")
    assert efficiency.value < 60


def test_analysis_source_is_heuristic() -> None:
    analysis = HeuristicAnalyzer().analyze(Prompt(content="Refactor parse_line in data/parser.py"))
    assert analysis.source == "heuristic"
    assert analysis.provider == "heuristic"
