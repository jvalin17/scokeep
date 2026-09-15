"""Python parity tests for scoreboard totals computation against shared test vectors.

Reads tests/vectors/scoreboard_vectors.json and runs each case against the pure
compute_scoreboard() function extracted from app/services/scoreboard.py.

Every vector drives assertions — this file must stay in sync with
tests/js/scoreboard.test.js which runs the same vectors in JS.
"""

import json
from pathlib import Path

import pytest

from app.services.scoreboard import compute_scoreboard

VECTORS_PATH = Path(__file__).parent.parent / "vectors" / "scoreboard_vectors.json"


def load_vectors() -> list[dict]:
    with VECTORS_PATH.open() as f:
        return json.load(f)


VECTORS = load_vectors()


class TestComputeScoreboardVectors:
    """Parametrised tests driven by scoreboard_vectors.json."""

    @pytest.mark.parametrize("vec", VECTORS, ids=[v["id"] for v in VECTORS])
    def test_totals(self, vec):
        result = compute_scoreboard(vec["rounds"], vec["player_count"])
        assert result["totals"] == vec["expected_totals"], (
            f"[{vec['id']}] Expected totals {vec['expected_totals']!r} "
            f"but got {result['totals']!r}. Description: {vec['description']}"
        )

    @pytest.mark.parametrize("vec", VECTORS, ids=[v["id"] for v in VECTORS])
    def test_rounds_passthrough(self, vec):
        result = compute_scoreboard(vec["rounds"], vec["player_count"])
        assert isinstance(result["rounds"], list)
        assert len(result["rounds"]) == len(vec["rounds"]), (
            f"[{vec['id']}] Expected {len(vec['rounds'])} rounds in output "
            f"but got {len(result['rounds'])}."
        )

    @pytest.mark.parametrize(
        "vec",
        [v for v in VECTORS if "expected_round_num" in v],
        ids=[v["id"] for v in VECTORS if "expected_round_num" in v],
    )
    def test_rounds_data_fields(self, vec):
        result = compute_scoreboard(vec["rounds"], vec["player_count"])
        assert result["rounds"][0]["round_num"] == vec["expected_round_num"]


class TestComputeScoreboardExplicit:
    """Explicit named tests — mirrors JS named tests in scoreboard.test.js."""

    def test_returns_totals_and_rounds_keys(self):
        result = compute_scoreboard([], 0)
        assert "totals" in result
        assert "rounds" in result

    def test_empty_rounds_with_player_count_fills_zeros(self):
        result = compute_scoreboard([], 2)
        assert result["totals"] == {"0": 0, "1": 0}

    def test_single_round_scores_become_totals(self):
        rounds = [
            {
                "round_num": 1,
                "cards_dealt": 8,
                "trump_suit": "hearts",
                "bids": {"0": 2, "1": 3},
                "hands_won": {"0": 2, "1": 3},
                "scores": {"0": 20, "1": 30},
            }
        ]
        result = compute_scoreboard(rounds, 2)
        assert result["totals"]["0"] == 20
        assert result["totals"]["1"] == 30

    def test_two_rounds_accumulate_scores(self):
        rounds = [
            {
                "round_num": 1,
                "cards_dealt": 8,
                "trump_suit": "clubs",
                "bids": {"0": 2},
                "hands_won": {"0": 2},
                "scores": {"0": 20},
            },
            {
                "round_num": 2,
                "cards_dealt": 7,
                "trump_suit": "diamonds",
                "bids": {"0": 1},
                "hands_won": {"0": 3},
                "scores": {"0": -10},
            },
        ]
        result = compute_scoreboard(rounds, 1)
        assert result["totals"]["0"] == 10

    def test_player_count_fills_missing_players_with_zero(self):
        rounds = [
            {
                "round_num": 1,
                "cards_dealt": 4,
                "trump_suit": "spades",
                "bids": {"0": 1},
                "hands_won": {"0": 1},
                "scores": {"0": 11},
            }
        ]
        result = compute_scoreboard(rounds, 3)
        assert result["totals"]["1"] == 0
        assert result["totals"]["2"] == 0

    def test_player_already_in_scores_not_overwritten_by_fill(self):
        rounds = [
            {
                "round_num": 1,
                "cards_dealt": 4,
                "trump_suit": "hearts",
                "bids": {"0": 2, "1": 1},
                "hands_won": {"0": 2, "1": 1},
                "scores": {"0": 20, "1": 11},
            }
        ]
        result = compute_scoreboard(rounds, 2)
        assert result["totals"]["0"] == 20
        assert result["totals"]["1"] == 11

    def test_rounds_data_passthrough_preserves_all_fields(self):
        rounds = [
            {
                "round_num": 3,
                "cards_dealt": 5,
                "trump_suit": "diamonds",
                "bids": {"0": 2},
                "hands_won": {"0": 2},
                "scores": {"0": 20},
            }
        ]
        result = compute_scoreboard(rounds, 1)
        assert result["rounds"][0]["round_num"] == 3
        assert result["rounds"][0]["cards_dealt"] == 5
        assert result["rounds"][0]["trump_suit"] == "diamonds"
        assert result["rounds"][0]["scores"] == {"0": 20}

    def test_negative_cumulative_total_when_player_misses_bids(self):
        rounds = [
            {
                "round_num": 1,
                "cards_dealt": 5,
                "trump_suit": "clubs",
                "bids": {"0": 3},
                "hands_won": {"0": 1},
                "scores": {"0": -30},
            },
            {
                "round_num": 2,
                "cards_dealt": 4,
                "trump_suit": "hearts",
                "bids": {"0": 2},
                "hands_won": {"0": 4},
                "scores": {"0": -20},
            },
        ]
        result = compute_scoreboard(rounds, 1)
        assert result["totals"]["0"] == -50

    def test_compute_scoreboard_returns_totals_dict(self):
        result = compute_scoreboard([], 2)
        assert "totals" in result
        assert result["totals"] == {"0": 0, "1": 0}

    def test_pure_function_does_not_mutate_input_rounds(self):
        rounds = [
            {
                "round_num": 1,
                "cards_dealt": 4,
                "trump_suit": "spades",
                "bids": {"0": 1},
                "hands_won": {"0": 1},
                "scores": {"0": 11},
            }
        ]
        original_length = len(rounds)
        compute_scoreboard(rounds, 1)
        assert len(rounds) == original_length
