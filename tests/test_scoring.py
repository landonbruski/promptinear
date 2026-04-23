from __future__ import annotations

from itertools import pairwise

import pytest

from promptinear.scoring import (
    clamp,
    curve_dimension,
    curve_grade,
    estimate_tokens,
    letter_grade,
)


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (100, "A+"),
        (97, "A+"),
        (93, "A"),
        (90, "A-"),
        (87, "B+"),
        (80, "B-"),
        (73, "C"),
        (60, "D-"),
        (59, "F"),
        (0, "F"),
    ],
)
def test_letter_grade(score: float, expected: str) -> None:
    assert letter_grade(score) == expected


def test_clamp_bounds() -> None:
    assert clamp(-5) == 0
    assert clamp(150) == 100
    assert clamp(50) == 50


def test_curve_monotonic() -> None:
    curved = [curve_grade(x) for x in range(0, 101, 5)]
    for a, b in pairwise(curved):
        assert b >= a


def test_curve_dimension_range() -> None:
    assert curve_dimension(0) == 0
    assert curve_dimension(100) <= 100
    assert curve_dimension(50) > 0


def test_estimate_tokens_zero_waste_when_perfect() -> None:
    t = estimate_tokens("short prompt", overall_grade=100)
    assert t.tokens_wasted == 0
    assert t.dollars_wasted == 0.0


def test_estimate_tokens_scales_with_length() -> None:
    short = estimate_tokens("abc", overall_grade=50)
    long = estimate_tokens("a" * 400, overall_grade=50)
    assert long.input_tokens > short.input_tokens
    assert long.tokens_wasted >= short.tokens_wasted
