"""Phase state machine parity tests.

Tests pure Python equivalents of GameService.advance_round and
GameService.extend_game against the shared vector file at
tests/vectors/phase_vectors.json.

The pure functions are extracted here (no DB, no ORM) so that the same
logic can be verified in both Python and JS from one source of truth.
"""

import copy
import json
from pathlib import Path

import pytest

VECTORS_PATH = Path(__file__).parent.parent / "vectors" / "phase_vectors.json"

DEFAULT_ROUNDS_PER_SET = 8


# ---------------------------------------------------------------------------
# Pure functions extracted from GameService (no DB, no ORM)
# ---------------------------------------------------------------------------


def advance_round(game: dict) -> dict:
    """Pure version of GameService.advance_round.

    Returns a new game dict; does not mutate the input.
    """
    g = copy.deepcopy(game)
    if g["current_round"] >= g["total_rounds"]:
        g["phase"] = "review"
    else:
        g["current_round"] += 1
        g["dealer_index"] = (g["dealer_index"] + 1) % len(g["players"])
        g["phase"] = "bidding"
    return g


def extend_game(game: dict) -> dict:
    """Pure version of GameService.extend_game.

    Returns a new game dict; does not mutate the input.
    """
    g = copy.deepcopy(game)
    rounds_per_set = g["settings"].get("rounds_per_set", DEFAULT_ROUNDS_PER_SET)
    g["total_rounds"] += rounds_per_set
    num_sets = g["settings"].get("num_sets", 3) + 1
    g["settings"] = {**g["settings"], "num_sets": num_sets}
    return g


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_vectors() -> dict:
    return json.loads(VECTORS_PATH.read_text())


# ---------------------------------------------------------------------------
# advance_round vector tests
# ---------------------------------------------------------------------------


class TestAdvanceRoundVectors:
    @pytest.fixture(autouse=True)
    def _vectors(self):
        self.vectors = load_vectors()["advance_round"]

    def _run(self, vec_id: str) -> tuple[dict, dict]:
        vec = next(v for v in self.vectors if v["id"] == vec_id)
        result = advance_round(vec["input"])
        return result, vec["expected"]

    def test_mid_game(self):
        result, expected = self._run("mid_game")
        assert result["current_round"] == expected["current_round"]
        assert result["dealer_index"] == expected["dealer_index"]
        assert result["phase"] == expected["phase"]
        assert result["total_rounds"] == expected["total_rounds"]

    def test_last_round_to_review(self):
        result, expected = self._run("last_round_to_review")
        assert result["phase"] == "review"
        assert result["current_round"] == expected["current_round"]
        assert result["dealer_index"] == expected["dealer_index"]

    def test_dealer_wrap(self):
        result, expected = self._run("dealer_wrap")
        assert result["dealer_index"] == 0
        assert result["phase"] == "bidding"
        assert result["current_round"] == expected["current_round"]

    def test_two_player_dealer_wrap(self):
        result, expected = self._run("two_player_dealer_wrap")
        assert result["dealer_index"] == 0
        assert result["phase"] == "bidding"

    def test_beyond_last_round(self):
        result, expected = self._run("beyond_last_round")
        assert result["phase"] == "review"
        assert result["current_round"] == expected["current_round"]


class TestAdvanceRoundPurity:
    def test_does_not_mutate_input(self):
        game = {
            "current_round": 3,
            "total_rounds": 8,
            "dealer_index": 1,
            "players": ["Alice", "Bob", "Carol"],
            "phase": "scoring",
        }
        original = copy.deepcopy(game)
        advance_round(game)
        assert game == original

    def test_returns_new_object(self):
        game = {
            "current_round": 3,
            "total_rounds": 8,
            "dealer_index": 1,
            "players": ["Alice", "Bob", "Carol"],
            "phase": "scoring",
        }
        result = advance_round(game)
        assert result is not game


# ---------------------------------------------------------------------------
# extend_game vector tests
# ---------------------------------------------------------------------------


class TestExtendGameVectors:
    @pytest.fixture(autouse=True)
    def _vectors(self):
        self.vectors = load_vectors()["extend_game"]

    def _run(self, vec_id: str) -> tuple[dict, dict]:
        vec = next(v for v in self.vectors if v["id"] == vec_id)
        result = extend_game(vec["input"])
        return result, vec["expected"]

    def test_default_extend(self):
        result, expected = self._run("default_extend")
        assert result["total_rounds"] == expected["total_rounds"]
        assert result["settings"]["num_sets"] == expected["settings"]["num_sets"]
        assert result["current_round"] == expected["current_round"]
        assert result["phase"] == expected["phase"]

    def test_extend_missing_rounds_per_set(self):
        result, expected = self._run("extend_missing_rounds_per_set")
        assert result["total_rounds"] == expected["total_rounds"]
        assert result["settings"]["num_sets"] == expected["settings"]["num_sets"]

    def test_extend_custom_rounds_per_set(self):
        result, expected = self._run("extend_custom_rounds_per_set")
        assert result["total_rounds"] == expected["total_rounds"]
        assert result["settings"]["num_sets"] == expected["settings"]["num_sets"]
        assert result["settings"]["rounds_per_set"] == 6


class TestExtendGamePurity:
    def test_does_not_mutate_input(self):
        game = {
            "current_round": 8,
            "total_rounds": 24,
            "dealer_index": 0,
            "players": ["Alice", "Bob"],
            "phase": "review",
            "settings": {"rounds_per_set": 8, "num_sets": 3},
        }
        original = copy.deepcopy(game)
        extend_game(game)
        assert game == original

    def test_does_not_mutate_nested_settings(self):
        settings = {"rounds_per_set": 8, "num_sets": 3}
        game = {
            "current_round": 8,
            "total_rounds": 24,
            "dealer_index": 0,
            "players": ["Alice", "Bob"],
            "phase": "review",
            "settings": settings,
        }
        extend_game(game)
        assert settings["num_sets"] == 3

    def test_returns_new_object(self):
        game = {
            "current_round": 8,
            "total_rounds": 24,
            "dealer_index": 0,
            "players": ["Alice", "Bob"],
            "phase": "review",
            "settings": {"rounds_per_set": 8, "num_sets": 3},
        }
        result = extend_game(game)
        assert result is not game
        assert result["settings"] is not game["settings"]
