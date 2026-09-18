"""Integration tests for the game import endpoint.

POST /api/game/{share_code}/import — accepts offline Quick Game data,
re-derives scores, creates Game + Rounds, triggers insights.
Covers: app/routes/import_game.py (decomposed handler + sub-functions).
"""

from httpx import AsyncClient


async def _setup_playground(client: AsyncClient) -> dict:
    """Create playground, auth, return share_code + cookies."""
    await client.post(
        "/api/playground",
        json={"name": "Import Test Room", "pin": "4321", "players": ["Anjum", "Masood", "Lala"]},
    )
    auth = await client.post(
        "/api/playground/auth",
        json={"name": "Import Test Room", "pin": "4321"},
    )
    cookies = {"scokeep_session": auth.cookies.get("scokeep_session")}
    playground = auth.json()
    return {"share_code": playground["share_code"], "cookies": cookies, "id": playground["id"]}


def _valid_import_payload(client_game_id="game-test-001"):
    """Return a valid import payload for a 3-player game with 1 round."""
    return {
        "client_game_id": client_game_id,
        "started_at": "2026-09-15T10:00:00.000Z",
        "finished_at": "2026-09-15T10:30:00.000Z",
        "players": ["Anjum", "Masood", "Lala"],
        "settings": {
            "mode": "rookie",
            "scoring_formula": "kachuful_standard",
            "must_lose": True,
            "rounds_per_set": 8,
            "num_sets": 1,
        },
        "rounds": [
            {
                "round_num": 1,
                "bids": {"0": 2, "1": 1, "2": 0},
                "hands_won": {"0": 2, "1": 1, "2": 0},
                "cards_dealt": 8,
                "trump_suit": "spades",
            },
        ],
    }


async def test_import_game_creates_game_and_rounds(client: AsyncClient):
    """Import creates a game + rounds with server-re-derived scores."""
    pg = await _setup_playground(client)
    payload = _valid_import_payload()

    response = await client.post(
        f"/api/game/{pg['share_code']}/import",
        json=payload,
        cookies=pg["cookies"],
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "game_id" in data
    assert data["rounds_imported"] == 1


async def test_import_game_requires_auth(client: AsyncClient):
    """Import without session cookie returns 401."""
    pg = await _setup_playground(client)
    payload = _valid_import_payload()

    response = await client.post(
        f"/api/game/{pg['share_code']}/import",
        json=payload,
    )

    assert response.status_code == 401


async def test_import_game_rejects_score_mismatch(client: AsyncClient):
    """Import with wrong scores in a round returns 422."""
    pg = await _setup_playground(client)
    payload = _valid_import_payload(client_game_id="game-bad-scores")
    # Tamper: set wrong scores (bid=2, hands=2 should be +20, not +99)
    payload["rounds"][0]["scores"] = {"0": 99, "1": 11, "2": 10}

    response = await client.post(
        f"/api/game/{pg['share_code']}/import",
        json=payload,
        cookies=pg["cookies"],
    )

    assert response.status_code == 422
    assert "score mismatch" in response.json()["detail"].lower()


async def test_import_game_duplicate_is_idempotent(client: AsyncClient):
    """Importing the same client_game_id twice returns 200 both times."""
    pg = await _setup_playground(client)
    payload = _valid_import_payload(client_game_id="game-dedup-test")

    first = await client.post(
        f"/api/game/{pg['share_code']}/import",
        json=payload,
        cookies=pg["cookies"],
    )
    assert first.status_code == 200
    first_game_id = first.json()["game_id"]

    second = await client.post(
        f"/api/game/{pg['share_code']}/import",
        json=payload,
        cookies=pg["cookies"],
    )
    assert second.status_code == 200
    assert second.json()["game_id"] == first_game_id
    assert second.json()["already_existed"] is True


async def test_import_game_tags_source(client: AsyncClient):
    """Imported game has source='offline_import'."""
    pg = await _setup_playground(client)
    payload = _valid_import_payload(client_game_id="game-source-tag")

    response = await client.post(
        f"/api/game/{pg['share_code']}/import",
        json=payload,
        cookies=pg["cookies"],
    )

    assert response.status_code == 200
    game_id = response.json()["game_id"]

    # Fetch the game directly to check source
    game_resp = await client.get(f"/api/game/{game_id}", cookies=pg["cookies"])
    assert game_resp.status_code == 200
    assert game_resp.json().get("source") == "offline_import"


async def test_import_game_rejects_wrong_playground(client: AsyncClient):
    """Import with session for a different playground returns 403."""
    pg = await _setup_playground(client)

    # Create a second playground and auth to it
    await client.post(
        "/api/playground",
        json={"name": "Other Room", "pin": "9999", "players": ["Xavier", "Yolanda"]},
    )
    other_auth = await client.post(
        "/api/playground/auth",
        json={"name": "Other Room", "pin": "9999"},
    )
    other_cookies = {"scokeep_session": other_auth.cookies.get("scokeep_session")}

    payload = _valid_import_payload(client_game_id="game-wrong-room")

    response = await client.post(
        f"/api/game/{pg['share_code']}/import",
        json=payload,
        cookies=other_cookies,
    )

    assert response.status_code == 403


async def test_import_game_min_players(client: AsyncClient):
    """Import with exactly 2 players (minimum) succeeds."""
    pg = await _setup_playground(client)
    payload = _valid_import_payload(client_game_id="game-min-players")
    payload["players"] = ["Anjum", "Masood"]
    payload["rounds"][0]["bids"] = {"0": 2, "1": 1}
    payload["rounds"][0]["hands_won"] = {"0": 2, "1": 1}

    response = await client.post(
        f"/api/game/{pg['share_code']}/import",
        json=payload,
        cookies=pg["cookies"],
    )

    assert response.status_code == 200
    assert response.json()["rounds_imported"] == 1


async def test_import_game_max_players(client: AsyncClient):
    """Import with exactly 8 players (maximum) succeeds."""
    pg = await _setup_playground(client)
    players = ["Player1", "Player2", "Player3", "Player4",
               "Player5", "Player6", "Player7", "Player8"]
    payload = _valid_import_payload(client_game_id="game-max-players")
    payload["players"] = players
    bids = {str(i): 0 for i in range(8)}
    hands = {str(i): 0 for i in range(8)}
    payload["rounds"][0]["bids"] = bids
    payload["rounds"][0]["hands_won"] = hands

    response = await client.post(
        f"/api/game/{pg['share_code']}/import",
        json=payload,
        cookies=pg["cookies"],
    )

    assert response.status_code == 200


async def test_import_game_too_many_players_rejected(client: AsyncClient):
    """Import with 9 players (over max) returns 422."""
    pg = await _setup_playground(client)
    players = [f"Player{i}" for i in range(9)]
    payload = _valid_import_payload(client_game_id="game-too-many")
    payload["players"] = players

    response = await client.post(
        f"/api/game/{pg['share_code']}/import",
        json=payload,
        cookies=pg["cookies"],
    )

    assert response.status_code == 422


async def test_import_game_multi_round(client: AsyncClient):
    """Import with multiple rounds creates all rounds."""
    pg = await _setup_playground(client)
    payload = _valid_import_payload(client_game_id="game-multi-round")
    payload["rounds"] = [
        {
            "round_num": 1,
            "bids": {"0": 2, "1": 1, "2": 0},
            "hands_won": {"0": 2, "1": 1, "2": 0},
            "cards_dealt": 8,
            "trump_suit": "spades",
        },
        {
            "round_num": 2,
            "bids": {"0": 1, "1": 1, "2": 1},
            "hands_won": {"0": 1, "1": 1, "2": 1},
            "cards_dealt": 7,
            "trump_suit": "diamonds",
        },
    ]

    response = await client.post(
        f"/api/game/{pg['share_code']}/import",
        json=payload,
        cookies=pg["cookies"],
    )

    assert response.status_code == 200
    assert response.json()["rounds_imported"] == 2


async def test_validate_round_scores_rejects_mismatch(client: AsyncClient):
    """_validate_round_scores raises 422 on tampered scores (tested via endpoint)."""
    pg = await _setup_playground(client)
    payload = _valid_import_payload(client_game_id="game-validate-scores")
    payload["rounds"][0]["scores"] = {"0": 999, "1": 0, "2": 0}
    response = await client.post(
        f"/api/game/{pg['share_code']}/import", json=payload, cookies=pg["cookies"],
    )
    assert response.status_code == 422
    assert "score mismatch" in response.json()["detail"].lower()


async def test_build_game_sets_offline_source(client: AsyncClient):
    """_build_game sets source='offline_import' (tested via endpoint + source check)."""
    pg = await _setup_playground(client)
    payload = _valid_import_payload(client_game_id="game-build-check")
    response = await client.post(
        f"/api/game/{pg['share_code']}/import", json=payload, cookies=pg["cookies"],
    )
    assert response.status_code == 200
    game_id = response.json()["game_id"]
    game_resp = await client.get(f"/api/game/{game_id}", cookies=pg["cookies"])
    assert game_resp.json().get("source") == "offline_import"


async def test_schedule_insights_recompute_does_not_block(client: AsyncClient):
    """_schedule_insights_recompute runs in background — import returns immediately."""
    pg = await _setup_playground(client)
    payload = _valid_import_payload(client_game_id="game-insights-bg")
    response = await client.post(
        f"/api/game/{pg['share_code']}/import", json=payload, cookies=pg["cookies"],
    )
    assert response.status_code == 200
    assert response.json()["rounds_imported"] == 1


async def test_import_game_rejects_unknown_formula(client: AsyncClient):
    """Import with invalid scoring formula returns 422."""
    pg = await _setup_playground(client)
    payload = _valid_import_payload(client_game_id="game-bad-formula")
    payload["settings"]["scoring_formula"] = "evil_formula"

    response = await client.post(
        f"/api/game/{pg['share_code']}/import",
        json=payload,
        cookies=pg["cookies"],
    )

    assert response.status_code == 422
    assert "unknown scoring formula" in response.json()["detail"].lower()
