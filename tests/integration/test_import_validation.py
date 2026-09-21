"""Tests for import endpoint input validation.

Security: validates that imported game data is plausible —
bids/hands keys match players, values within card bounds,
hands_won sum doesn't exceed cards dealt.
"""

import pytest
from httpx import AsyncClient


async def _setup_playground(client: AsyncClient):
    """Create playground and return (playground_id, share_code, cookies)."""
    await client.post(
        "/api/playground",
        json={"name": "Import Validation", "pin": "1234", "players": ["A", "B", "C"]},
    )
    auth = await client.post(
        "/api/playground/auth",
        json={"name": "Import Validation", "pin": "1234"},
    )
    cookies = {"scokeep_session": auth.cookies.get("scokeep_session")}
    pg = auth.json()
    return pg["id"], pg["share_code"], cookies


def _valid_round(round_num=1, cards_dealt=8):
    """A valid round with 3 players, all bids/hands within bounds."""
    return {
        "round_num": round_num,
        "bids": {"0": 2, "1": 3, "2": 1},
        "hands_won": {"0": 2, "1": 3, "2": 3},
        "cards_dealt": cards_dealt,
        "trump_suit": "spades",
    }


def _valid_import_body(rounds=None):
    """A valid import request body."""
    return {
        "client_game_id": "test-import-valid-001",
        "started_at": "2026-09-20T12:00:00",
        "finished_at": "2026-09-20T13:00:00",
        "players": ["A", "B", "C"],
        "settings": {"mode": "expert", "rounds_per_set": 8, "scoring_formula": "kachuful_standard"},
        "rounds": rounds or [_valid_round()],
    }


def test_validate_round_data_rejects_bad_keys():
    """Direct test for the model_validator function."""
    from pydantic import ValidationError

    from app.schemas.import_game import ImportGameRequest

    with pytest.raises(ValidationError):
        ImportGameRequest(
            client_game_id="test-direct-001",
            started_at="2026-09-20T12:00:00",
            finished_at="2026-09-20T13:00:00",
            players=["A", "B"],
            settings={"scoring_formula": "kachuful_standard"},
            rounds=[{
                "round_num": 1,
                "bids": {"0": 1, "99": 1},
                "hands_won": {"0": 1, "1": 1},
                "cards_dealt": 8,
                "trump_suit": "spades",
            }],
        )


class TestImportValidation:
    """Import endpoint must reject invalid bids/hands data."""

    async def test_import_allows_valid_game(self, client: AsyncClient):
        """Baseline: a valid import succeeds."""
        pg_id, share_code, cookies = await _setup_playground(client)
        body = _valid_import_body()
        resp = await client.post(
            f"/api/game/{share_code}/import", json=body, cookies=cookies,
        )
        assert resp.status_code == 200, f"Valid import failed: {resp.text}"

    async def test_import_rejects_mismatched_bid_keys(self, client: AsyncClient):
        """Bids keys must match player indices {0, 1, 2} for 3 players."""
        pg_id, share_code, cookies = await _setup_playground(client)
        body = _valid_import_body(rounds=[{
            "round_num": 1,
            "bids": {"0": 2, "1": 3, "99": 1},  # key "99" doesn't match any player
            "hands_won": {"0": 2, "1": 3, "2": 3},
            "cards_dealt": 8,
            "trump_suit": "spades",
        }])
        resp = await client.post(
            f"/api/game/{share_code}/import", json=body, cookies=cookies,
        )
        assert resp.status_code == 422, f"Expected 422 for bad bid keys, got {resp.status_code}"

    async def test_import_rejects_mismatched_hands_keys(self, client: AsyncClient):
        """Hands_won keys must match player indices."""
        pg_id, share_code, cookies = await _setup_playground(client)
        body = _valid_import_body(rounds=[{
            "round_num": 1,
            "bids": {"0": 2, "1": 3, "2": 1},
            "hands_won": {"0": 2, "1": 3, "X": 3},  # key "X" invalid
            "cards_dealt": 8,
            "trump_suit": "spades",
        }])
        resp = await client.post(
            f"/api/game/{share_code}/import", json=body, cookies=cookies,
        )
        assert resp.status_code == 422, f"Expected 422 for bad hands keys, got {resp.status_code}"

    async def test_import_rejects_hands_sum_exceeds_cards(self, client: AsyncClient):
        """sum(hands_won) must not exceed cards_dealt."""
        pg_id, share_code, cookies = await _setup_playground(client)
        body = _valid_import_body(rounds=[{
            "round_num": 1,
            "bids": {"0": 2, "1": 3, "2": 1},
            "hands_won": {"0": 5, "1": 5, "2": 5},  # sum=15, cards=8
            "cards_dealt": 8,
            "trump_suit": "spades",
        }])
        resp = await client.post(
            f"/api/game/{share_code}/import", json=body, cookies=cookies,
        )
        assert resp.status_code == 422, f"Expected 422 for hands sum, got {resp.status_code}"

    async def test_import_rejects_bid_out_of_range(self, client: AsyncClient):
        """Each bid must be 0 <= bid <= cards_dealt."""
        pg_id, share_code, cookies = await _setup_playground(client)
        body = _valid_import_body(rounds=[{
            "round_num": 1,
            "bids": {"0": 2, "1": 99, "2": 1},  # bid 99 > cards_dealt 8
            "hands_won": {"0": 2, "1": 3, "2": 3},
            "cards_dealt": 8,
            "trump_suit": "spades",
        }])
        resp = await client.post(
            f"/api/game/{share_code}/import", json=body, cookies=cookies,
        )
        assert resp.status_code == 422, f"Expected 422 for bid out of range, got {resp.status_code}"

    async def test_import_rejects_negative_bid(self, client: AsyncClient):
        """Negative bids are invalid."""
        pg_id, share_code, cookies = await _setup_playground(client)
        body = _valid_import_body(rounds=[{
            "round_num": 1,
            "bids": {"0": -1, "1": 3, "2": 1},
            "hands_won": {"0": 2, "1": 3, "2": 3},
            "cards_dealt": 8,
            "trump_suit": "spades",
        }])
        resp = await client.post(
            f"/api/game/{share_code}/import", json=body, cookies=cookies,
        )
        assert resp.status_code == 422, f"Expected 422 for negative bid, got {resp.status_code}"

    async def test_import_rejects_negative_hands_won(self, client: AsyncClient):
        """Negative hands_won values are invalid."""
        pg_id, share_code, cookies = await _setup_playground(client)
        body = _valid_import_body(rounds=[{
            "round_num": 1,
            "bids": {"0": 2, "1": 3, "2": 1},
            "hands_won": {"0": -1, "1": 3, "2": 3},
            "cards_dealt": 8,
            "trump_suit": "spades",
        }])
        resp = await client.post(
            f"/api/game/{share_code}/import", json=body, cookies=cookies,
        )
        assert resp.status_code == 422, f"Expected 422 for negative hands, got {resp.status_code}"

    async def test_import_rejects_finished_before_started(self, client: AsyncClient):
        """finished_at must be >= started_at."""
        pg_id, share_code, cookies = await _setup_playground(client)
        body = _valid_import_body()
        body["started_at"] = "2026-09-20T14:00:00"
        body["finished_at"] = "2026-09-20T12:00:00"  # before started
        resp = await client.post(
            f"/api/game/{share_code}/import", json=body, cookies=cookies,
        )
        assert resp.status_code == 422, f"Expected 422 for bad timestamps, got {resp.status_code}"

    async def test_import_rejects_duplicate_round_nums(self, client: AsyncClient):
        """Round numbers must be unique."""
        pg_id, share_code, cookies = await _setup_playground(client)
        body = _valid_import_body(rounds=[
            _valid_round(round_num=1),
            _valid_round(round_num=1),  # duplicate
        ])
        body["client_game_id"] = "test-dup-rounds-001"
        resp = await client.post(
            f"/api/game/{share_code}/import", json=body, cookies=cookies,
        )
        assert resp.status_code == 422, f"Expected 422 for dup round_nums, got {resp.status_code}"
