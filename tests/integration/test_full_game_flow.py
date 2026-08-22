"""End-to-end integration test: full game flow with realistic frontend settings.

Exercises the exact settings the frontend sends — catches schema mismatches
like timer_seconds=3 being rejected by ge=5 validation.
"""

from httpx import AsyncClient

FRONTEND_DEFAULT_SETTINGS = {
    "mode": "rookie",
    "appearance": "interactive",
    "timer_seconds": 3,
    "num_sets": 1,
    "must_lose": True,
}


async def _create_playground_and_auth(client: AsyncClient, name: str = "E2E Test"):
    await client.post(
        "/api/playground",
        json={
            "name": name,
            "pin": "1234",
            "players": ["Alice", "Bob", "Charlie"],
        },
    )
    auth = await client.post(
        "/api/playground/auth",
        json={
            "name": name,
            "pin": "1234",
        },
    )
    cookies = {"scokeep_session": auth.cookies.get("scokeep_session")}
    return auth.json(), cookies


class TestFullGameFlow:
    """Simulates an entire game as the frontend would drive it."""

    async def test_create_game_with_frontend_defaults(self, client: AsyncClient):
        """Game creation with exact frontend default settings must succeed."""
        pg, cookies = await _create_playground_and_auth(client)

        response = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": ["Alice", "Bob", "Charlie"],
                "settings": FRONTEND_DEFAULT_SETTINGS,
            },
            cookies=cookies,
        )

        assert response.status_code == 201
        body = response.json()
        assert body["settings"]["timer_seconds"] == 3
        assert body["settings"]["appearance"] == "interactive"
        assert body["settings"]["must_lose"] is True
        assert body["total_rounds"] == 8

    async def test_full_round_with_frontend_settings(self, client: AsyncClient):
        """Complete one round: bid -> confirm -> play -> hands -> score."""
        pg, cookies = await _create_playground_and_auth(client, "Full Round E2E")

        # Create game
        game_resp = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": ["Alice", "Bob", "Charlie"],
                "settings": FRONTEND_DEFAULT_SETTINGS,
            },
            cookies=cookies,
        )
        assert game_resp.status_code == 201
        game_id = game_resp.json()["id"]

        # Bid (8 cards, must-lose on, 3 players)
        for i, bid in enumerate([2, 3, 1]):
            resp = await client.post(
                f"/api/game/{game_id}/bid",
                json={
                    "player_index": i,
                    "value": bid,
                },
                cookies=cookies,
            )
            assert resp.status_code == 200

        # Confirm bids
        resp = await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
        assert resp.status_code == 200

        # Enter round end
        resp = await client.post(
            f"/api/game/{game_id}/enter-round-end",
            cookies=cookies,
        )
        assert resp.status_code == 200

        # Submit hands
        for i, hands in enumerate([2, 3, 1]):
            resp = await client.post(
                f"/api/game/{game_id}/hands",
                json={
                    "player_index": i,
                    "value": hands,
                },
                cookies=cookies,
            )
            assert resp.status_code == 200

        # Score round
        resp = await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)
        assert resp.status_code == 200
        scores = resp.json()["scores"]
        assert scores == {"0": 20, "1": 30, "2": 11}

        # Check scoreboard
        resp = await client.get(
            f"/api/game/{game_id}/scoreboard",
            cookies=cookies,
        )
        assert resp.status_code == 200
        assert resp.json()["totals"] == {"0": 20, "1": 30, "2": 11}

        # Game should be on scoreboard phase, still round 1
        resp = await client.get(f"/api/game/{game_id}", cookies=cookies)
        assert resp.json()["phase"] == "scoreboard"
        assert resp.json()["current_round"] == 1

    async def test_must_lose_blocks_last_player_via_api(self, client: AsyncClient):
        """Must-lose enforcement through the API (not just service)."""
        pg, cookies = await _create_playground_and_auth(client, "Must Lose E2E")

        game_resp = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": ["Alice", "Bob", "Charlie"],
                "settings": FRONTEND_DEFAULT_SETTINGS,
            },
            cookies=cookies,
        )
        game_id = game_resp.json()["id"]

        # First two players bid: 3 + 2 = 5
        await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 0,
                "value": 3,
            },
            cookies=cookies,
        )
        await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 1,
                "value": 2,
            },
            cookies=cookies,
        )

        # Last player bids 3 -> total=8=cards, must-lose blocks
        resp = await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 2,
                "value": 3,
            },
            cookies=cookies,
        )
        assert resp.status_code == 409
        assert "must-lose" in resp.json()["detail"]

        # Last player bids 2 -> total=7!=8, allowed
        resp = await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 2,
                "value": 2,
            },
            cookies=cookies,
        )
        assert resp.status_code == 200

    async def test_recent_playgrounds_returns_names(self, client: AsyncClient):
        """Recent playgrounds endpoint works after creating playgrounds."""
        await _create_playground_and_auth(client, "Recent Test 1")
        await _create_playground_and_auth(client, "Recent Test 2")

        resp = await client.get("/api/playground/recent")
        assert resp.status_code == 200
        names = resp.json()["names"]
        assert "Recent Test 1" in names
        assert "Recent Test 2" in names
