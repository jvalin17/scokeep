"""Parity tests: JSON vectors must match Python scoring engine output.

These tests validate that scoring_vectors.json and round_scoring_vectors.json
are correct by asserting them against the authoritative Python implementation.
They must always pass — they are the source of truth for the JS port.
"""

import json
from pathlib import Path

import pytest

from app.services.scoring import (
    calculate_round_scores,
    kachuful_standard,
    kachuful_zeros,
)

VECTORS_DIR = Path(__file__).parent.parent / "vectors"

FORMULA_FN = {
    "kachuful_standard": kachuful_standard,
    "kachuful_zeros": kachuful_zeros,
}


def load_scoring_vectors():
    return json.loads((VECTORS_DIR / "scoring_vectors.json").read_text())


def load_round_vectors():
    return json.loads((VECTORS_DIR / "round_scoring_vectors.json").read_text())


class TestScoringVectorParity:
    """Each vector triple (bid, actual, expected) must match Python formula output."""

    @pytest.mark.parametrize("case", load_scoring_vectors()["kachuful_standard"])
    def test_kachuful_standard(self, case):
        result = kachuful_standard(bid=case["bid"], actual=case["actual"])
        assert result == case["expected"], (
            f"kachuful_standard(bid={case['bid']}, actual={case['actual']}) "
            f"returned {result}, expected {case['expected']}"
        )

    @pytest.mark.parametrize("case", load_scoring_vectors()["kachuful_zeros"])
    def test_kachuful_zeros(self, case):
        result = kachuful_zeros(bid=case["bid"], actual=case["actual"])
        assert result == case["expected"], (
            f"kachuful_zeros(bid={case['bid']}, actual={case['actual']}) "
            f"returned {result}, expected {case['expected']}"
        )


class TestRoundScoringVectorParity:
    """Each round vector must match Python calculate_round_scores output."""

    @pytest.mark.parametrize("case", load_round_vectors()["kachuful_standard"])
    def test_kachuful_standard_round(self, case):
        result = calculate_round_scores(
            bids=case["bids"],
            hands_won=case["hands_won"],
            formula_name="kachuful_standard",
        )
        assert result == case["expected"], (
            f"Round '{case['description']}': got {result}, expected {case['expected']}"
        )

    @pytest.mark.parametrize("case", load_round_vectors()["kachuful_zeros"])
    def test_kachuful_zeros_round(self, case):
        result = calculate_round_scores(
            bids=case["bids"],
            hands_won=case["hands_won"],
            formula_name="kachuful_zeros",
        )
        assert result == case["expected"], (
            f"Round '{case['description']}': got {result}, expected {case['expected']}"
        )
