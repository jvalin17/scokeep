"""Parity test: validate hands_vectors.json against Python submit_hands logic.

These tests confirm the vectors are correct so JS tests can trust them.
Uses the production validate_hands() pure function from app/services/round.py.
"""

import json
from pathlib import Path

from app.services.round import validate_hands

VECTORS_PATH = Path(__file__).parent.parent / "vectors" / "hands_vectors.json"


def load_vectors():
    return json.loads(VECTORS_PATH.read_text())


class TestHandsVectorsMatchPython:
    """Each vector must produce the expected valid/invalid result."""

    def test_validate_hands_all_vectors(self):
        vectors = load_vectors()
        for entry in vectors["validate_hands"]:
            result = validate_hands(
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
            result = validate_hands(
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
            result = validate_hands(
                entry["existing_hands"],
                entry["player_index"],
                entry["value"],
                entry["cards_dealt"],
            )
            assert isinstance(result, str), (
                f"[{entry['description']}] expected str error, got {result!r}"
            )


def test_validate_hands():
    """validate_hands returns None for valid input, str for invalid."""
    from app.services.round import validate_hands

    assert validate_hands({}, 0, 3, 8) is None
    assert isinstance(validate_hands({}, 0, -1, 8), str)
