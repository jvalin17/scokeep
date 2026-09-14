"""Parity test: validate hands_vectors.json against Python submit_hands logic.

These tests confirm the vectors are correct so JS tests can trust them.
The validation logic mirrors RoundService.submit_hands from app/services/round.py.
"""

import json
from pathlib import Path

VECTORS_PATH = Path(__file__).parent.parent / "vectors" / "hands_vectors.json"


def load_vectors():
    return json.loads(VECTORS_PATH.read_text())


def _validate_hands_python(existing_hands, player_index, value, cards_dealt):
    """Pure Python mirror of the validation in RoundService.submit_hands."""
    if value < 0:
        return f"Hands ({value}) cannot be negative"
    player_key = str(player_index)
    total_others = sum(v for k, v in existing_hands.items() if k != player_key)
    remaining = cards_dealt - total_others
    if value > remaining:
        return f"Hands ({value}) exceeds remaining cards ({remaining})"
    return None


class TestHandsVectorsMatchPython:
    """Each vector must produce the expected valid/invalid result."""

    def test_validate_hands_all_vectors(self):
        vectors = load_vectors()
        for entry in vectors["validate_hands"]:
            result = _validate_hands_python(
                entry["existing_hands"],
                entry["player_index"],
                entry["value"],
                entry["cards_dealt"],
            )
            if entry["valid"]:
                assert result is None, (
                    f"[{entry['description']}] expected valid (None) but got: {result!r}"
                )
            else:
                assert result is not None, (
                    f"[{entry['description']}] expected invalid (error string) but got None"
                )
                assert isinstance(result, str), (
                    f"[{entry['description']}] expected str error, got {type(result)}"
                )

    def test_validate_hands_valid_returns_none(self):
        vectors = load_vectors()
        for entry in vectors["validate_hands"]:
            if not entry["valid"]:
                continue
            result = _validate_hands_python(
                entry["existing_hands"],
                entry["player_index"],
                entry["value"],
                entry["cards_dealt"],
            )
            assert result is None, f"[{entry['description']}] expected None, got {result!r}"

    def test_validate_hands_invalid_returns_string(self):
        vectors = load_vectors()
        for entry in vectors["validate_hands"]:
            if entry["valid"]:
                continue
            result = _validate_hands_python(
                entry["existing_hands"],
                entry["player_index"],
                entry["value"],
                entry["cards_dealt"],
            )
            assert isinstance(result, str), (
                f"[{entry['description']}] expected str error, got {result!r}"
            )
