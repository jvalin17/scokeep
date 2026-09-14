"""Parity test: validate trump_vectors.json against Python implementations.

These tests confirm the vectors are correct so JS tests can trust them.
"""

import json
from pathlib import Path

from app.utils.trump import get_cards_for_round, get_trump_for_round, max_cards_for_players

VECTORS_PATH = Path(__file__).parent.parent / "vectors" / "trump_vectors.json"


def load_vectors():
    return json.loads(VECTORS_PATH.read_text())


class TestTrumpRotationVectors:
    """Each trump_rotation vector must match Python get_trump_for_round."""

    def test_trump_rotation_vectors_match_python(self):
        vectors = load_vectors()
        for entry in vectors["trump_rotation"]:
            result = get_trump_for_round(entry["round"])
            assert result == entry["trump"], (
                f"Round {entry['round']}: expected {entry['trump']!r}, got {result!r}"
            )

    def test_trump_rotation_returns_strings(self):
        vectors = load_vectors()
        for entry in vectors["trump_rotation"]:
            result = get_trump_for_round(entry["round"])
            assert isinstance(result, str), (
                f"Round {entry['round']}: expected str, got {type(result)}"
            )


class TestCardsPerRoundVectors:
    """Each cards_per_round vector must match Python get_cards_for_round."""

    def test_cards_per_round_vectors_match_python(self):
        vectors = load_vectors()
        for entry in vectors["cards_per_round"]:
            result = get_cards_for_round(entry["round"], entry["rounds_per_set"])
            assert result == entry["cards"], (
                f"Round {entry['round']} (rps={entry['rounds_per_set']}): "
                f"expected {entry['cards']}, got {result}"
            )

    def test_cards_per_round_returns_integers(self):
        vectors = load_vectors()
        for entry in vectors["cards_per_round"]:
            result = get_cards_for_round(entry["round"], entry["rounds_per_set"])
            assert isinstance(result, int), (
                f"Round {entry['round']}: expected int, got {type(result)}"
            )


class TestMaxCardsVectors:
    """Each max_cards vector must match Python max_cards_for_players."""

    def test_max_cards_vectors_match_python(self):
        vectors = load_vectors()
        for entry in vectors["max_cards"]:
            result = max_cards_for_players(entry["players"])
            assert result == entry["max_cards"], (
                f"Players {entry['players']}: expected {entry['max_cards']}, got {result}"
            )

    def test_max_cards_returns_integers(self):
        vectors = load_vectors()
        for entry in vectors["max_cards"]:
            result = max_cards_for_players(entry["players"])
            assert isinstance(result, int), (
                f"Players {entry['players']}: expected int, got {type(result)}"
            )
