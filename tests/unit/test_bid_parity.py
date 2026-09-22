"""Python parity tests for bid validation against shared test vectors.

Reads tests/vectors/bid_vectors.json and runs each case against the pure
validate_bid() function extracted from app/services/round.py.

Every vector drives one assertion — this file must stay in sync with
tests/js/bid-validation.test.js which runs the same vectors in JS.
"""

import json
from pathlib import Path

import pytest

from app.services.round import validate_bid

VECTORS_PATH = Path(__file__).parent.parent / "vectors" / "bid_vectors.json"


def load_vectors():
    with VECTORS_PATH.open() as f:
        return json.load(f)


VECTORS = load_vectors()


def _run_vector(vec: dict) -> str | None:
    return validate_bid(
        vec["existingBids"],
        vec["playerIndex"],
        vec["value"],
        must_lose=vec["mustLose"],
        cards_deal=vec["cardsDeal"],
        player_count=vec["playerCount"],
    )


class TestValidateBidVectors:
    """Parametrised tests driven by bid_vectors.json."""

    @pytest.mark.parametrize("vec", VECTORS, ids=[v["id"] for v in VECTORS])
    def test_vector(self, vec):
        result = _run_vector(vec)
        if vec["expectError"]:
            assert result is not None, (
                f"[{vec['id']}] Expected an error string but got None. "
                f"Description: {vec['description']}"
            )
            assert isinstance(result, str), (
                f"[{vec['id']}] Error return must be a string, got {type(result)}"
            )
        else:
            assert result is None, (
                f"[{vec['id']}] Expected None (valid bid) but got: {result!r}. "
                f"Description: {vec['description']}"
            )


class TestValidateBidMustLoseConstraint:
    """Explicit named tests for must-lose constraint — mirrors JS named tests."""

    def test_must_lose_last_player_rejected_when_total_equals_cards_dealt(self):
        result = validate_bid(
            {"0": 2, "1": 3},
            2,
            3,
            must_lose=True,
            cards_deal=8,
            player_count=3,
        )
        assert result is not None
        assert isinstance(result, str)

    def test_must_lose_last_player_allowed_when_total_differs(self):
        result = validate_bid(
            {"0": 2, "1": 3},
            2,
            2,
            must_lose=True,
            cards_deal=8,
            player_count=3,
        )
        assert result is None

    def test_must_lose_non_last_player_always_allowed(self):
        result = validate_bid(
            {"0": 4},
            1,
            4,
            must_lose=True,
            cards_deal=8,
            player_count=3,
        )
        assert result is None

    def test_must_lose_disabled_last_player_can_equalise_total(self):
        result = validate_bid(
            {"0": 2, "1": 3},
            2,
            3,
            must_lose=False,
            cards_deal=8,
            player_count=3,
        )
        assert result is None

    def test_one_card_round_last_player_bid_one_rejected(self):
        result = validate_bid(
            {"0": 0, "1": 0},
            2,
            1,
            must_lose=True,
            cards_deal=1,
            player_count=3,
        )
        assert result is not None

    def test_one_card_round_last_player_bid_zero_allowed(self):
        result = validate_bid(
            {"0": 0, "1": 0},
            2,
            0,
            must_lose=True,
            cards_deal=1,
            player_count=3,
        )
        assert result is None

    def test_duplicate_bid_rejected(self):
        result = validate_bid(
            {"0": 2, "1": 3},
            1,
            1,
            must_lose=False,
            cards_deal=8,
            player_count=3,
        )
        assert result is not None


class TestBid13CardRound:
    """13-card round support for bid validation."""

    def test_bid_13_accepted_when_cards_dealt_is_13(self):
        result = validate_bid(
            {},
            0,
            13,
            must_lose=False,
            cards_deal=13,
            player_count=4,
        )
        assert result is None

    def test_bid_14_rejected_when_cards_dealt_is_13(self):
        result = validate_bid(
            {},
            0,
            14,
            must_lose=False,
            cards_deal=13,
            player_count=4,
        )
        assert result is not None

    def test_must_lose_last_player_rejected_at_13(self):
        result = validate_bid(
            {"0": 5, "1": 3, "2": 2},
            3,
            3,
            must_lose=True,
            cards_deal=13,
            player_count=4,
        )
        assert result is not None

    def test_must_lose_last_player_allowed_when_not_equal_13(self):
        result = validate_bid(
            {"0": 5, "1": 3, "2": 2},
            3,
            4,
            must_lose=True,
            cards_deal=13,
            player_count=4,
        )
        assert result is None

    def test_negative_bid_rejected(self):
        result = validate_bid(
            {"0": 2},
            1,
            -1,
            must_lose=False,
            cards_deal=8,
            player_count=3,
        )
        assert result is not None

    def test_validate_bid_returns_none_for_valid(self):
        result = validate_bid({}, 0, 2, must_lose=False, cards_deal=8, player_count=3)
        assert result is None
