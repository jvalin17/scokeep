"""Integration tests for sync endpoints.

Tests server-side round sync validation and game state sync.
"""

from httpx import AsyncClient


async def _setup_game(client: AsyncClient, players=None, settings=None) -> dict:
    """Helper: create playground, auth, create game. Return game + cookies."""
    players = players or ["Alice", "Bob", "Charlie"]
    await client.post(
        "/api/playground",
        json={
            "name": "Sync Test Group",
            "pin": "5678",
            "players": players,
        },
    )
    auth = await client.post(
        "/api/playground/auth",
        json={"name": "Sync Test Group", "pin": "5678"},
    )
    cookies = {"scokeep_session": auth.cookies.get("scokeep_session")}
    pg = auth.json()

    game_body = {
        "playground_id": pg["id"],
        "players": players,
        "settings": settings or {"num_sets": 1},
    }
    game_resp = await client.post("/api/game", json=game_body, cookies=cookies)
    game = game_resp.json()
    return {**game, "cookies": cookies}


def _valid_sync_payload(bids=None, hands_won=None, scores=None):
    """Return a valid sync-round payload for a 3-player game (kachuful_standard).

    Round 1, 8 cards dealt.
    Defaults: each player bids 2 and wins 2 → score = 20.
    """
    bids = bids or {"0": 2, "1": 2, "2": 2}
    hands_won = hands_won or {"0": 2, "1": 2, "2": 2}
    # kachuful_standard: bid==actual, bid>=2 → bid*10
    scores = scores or {"0": 20, "1": 20, "2": 20}
    return {
        "round_num": 1,
        "cards_dealt": 8,
        "trump_suit": "spades",
        "bids": bids,
        "hands_won": hands_won,
        "scores": scores,
        "status": "scored",
    }


class TestSyncRoundAcceptsValidData:
    async def test_sync_round_accepts_valid_data(self, client: AsyncClient):
        game = await _setup_game(client)
        payload = _valid_sync_payload()

        response = await client.post(
            f"/api/game/{game['id']}/sync-round",
            json=payload,
            cookies=game["cookies"],
        )

        assert response.status_code == 200
        body = response.json()
        assert body["round_num"] == 1
        assert body["scores"] == {"0": 20, "1": 20, "2": 20}


class TestSyncRoundRejectsMismatchedScores:
    async def test_sync_round_rejects_mismatched_scores(self, client: AsyncClient):
        game = await _setup_game(client)
        # Claim wrong scores: say each player got 99 when they should have 20
        payload = _valid_sync_payload(scores={"0": 99, "1": 99, "2": 99})

        response = await client.post(
            f"/api/game/{game['id']}/sync-round",
            json=payload,
            cookies=game["cookies"],
        )

        assert response.status_code == 409
        assert "score" in response.json()["detail"].lower()


class TestSyncRoundCreatesRoundIfMissing:
    async def test_sync_round_creates_round_if_missing(self, client: AsyncClient):
        """Sync upserts — creates the Round row if none exists yet."""
        game = await _setup_game(client)
        payload = _valid_sync_payload()

        # No round has been created via normal API flow; sync should create it
        response = await client.post(
            f"/api/game/{game['id']}/sync-round",
            json=payload,
            cookies=game["cookies"],
        )

        assert response.status_code == 200

        # Verify via a second fetch that round now exists
        response2 = await client.post(
            f"/api/game/{game['id']}/sync-round",
            json=payload,
            cookies=game["cookies"],
        )
        assert response2.status_code == 200


class TestSyncRoundIdempotent:
    async def test_sync_round_idempotent(self, client: AsyncClient):
        """Sending the same payload twice returns 200 both times."""
        game = await _setup_game(client)
        payload = _valid_sync_payload()

        r1 = await client.post(
            f"/api/game/{game['id']}/sync-round",
            json=payload,
            cookies=game["cookies"],
        )
        r2 = await client.post(
            f"/api/game/{game['id']}/sync-round",
            json=payload,
            cookies=game["cookies"],
        )

        assert r1.status_code == 200
        assert r2.status_code == 200


class TestSyncRoundRequiresAuth:
    async def test_sync_round_requires_auth(self, client: AsyncClient):
        """No session cookie → 401."""
        game = await _setup_game(client)
        payload = _valid_sync_payload()

        response = await client.post(
            f"/api/game/{game['id']}/sync-round",
            json=payload,
            # no cookies
        )

        assert response.status_code == 401


class TestSyncRoundValidatesGameOwnership:
    async def test_sync_round_validates_game_ownership(self, client: AsyncClient):
        """Authenticated but wrong playground → 403."""
        game = await _setup_game(client)

        # Create a second playground and authenticate as them
        await client.post(
            "/api/playground",
            json={
                "name": "Other Group",
                "pin": "9999",
                "players": ["X", "Y"],
            },
        )
        other_auth = await client.post(
            "/api/playground/auth",
            json={"name": "Other Group", "pin": "9999"},
        )
        other_cookies = {"scokeep_session": other_auth.cookies.get("scokeep_session")}

        payload = _valid_sync_payload()

        response = await client.post(
            f"/api/game/{game['id']}/sync-round",
            json=payload,
            cookies=other_cookies,
        )

        assert response.status_code == 403


class TestSyncGameState:
    async def test_sync_game_state(self, client: AsyncClient):
        """POST /api/game/{id}/sync-state updates game phase/round/dealer."""
        game = await _setup_game(client)

        payload = {
            "phase": "playing",
            "current_round": 1,
            "dealer_index": 0,
            "status": "active",
        }

        response = await client.post(
            f"/api/game/{game['id']}/sync-state",
            json=payload,
            cookies=game["cookies"],
        )

        assert response.status_code == 200
        body = response.json()
        assert body["phase"] == "playing"
        assert body["current_round"] == 1
        assert body["dealer_index"] == 0

    async def test_sync_game_state_requires_auth(self, client: AsyncClient):
        game = await _setup_game(client)
        payload = {
            "phase": "playing",
            "current_round": 1,
            "dealer_index": 0,
            "status": "active",
        }

        response = await client.post(
            f"/api/game/{game['id']}/sync-state",
            json=payload,
            # no cookies
        )

        assert response.status_code == 401
