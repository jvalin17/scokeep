"""Integration tests for active game resume and TTL.

Tests the GET /api/game/active/{playground_id} endpoint which returns
the most recently updated active game within a 10-minute TTL window.
"""

from httpx import AsyncClient


async def _setup(client: AsyncClient, name: str = "Active Test"):
    """Create playground, auth, return (playground, cookies)."""
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


class TestActiveGame:
    """GET /api/game/active/{playground_id} — resume in-progress games."""

    async def test_returns_active_game(self, client: AsyncClient):
        """Active game endpoint returns the most recent active game."""
        pg, cookies = await _setup(client, "Active Resume Test")

        # Create a game
        game_resp = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": ["Alice", "Bob", "Charlie"],
                "settings": {"num_sets": 1},
            },
            cookies=cookies,
        )
        assert game_resp.status_code == 201
        game_id = game_resp.json()["id"]

        # Active game should return it
        resp = await client.get(
            f"/api/game/active/{pg['id']}",
            cookies=cookies,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == game_id
        assert resp.json()["status"] == "active"

    async def test_no_active_game_returns_404(self, client: AsyncClient):
        """When no active game exists, returns 404."""
        pg, cookies = await _setup(client, "No Active Test")

        resp = await client.get(
            f"/api/game/active/{pg['id']}",
            cookies=cookies,
        )
        assert resp.status_code == 404

    async def test_finished_game_not_returned(self, client: AsyncClient):
        """Finished games are not returned by the active endpoint."""
        pg, cookies = await _setup(client, "Finished Active Test")

        # Create and end a game
        game_resp = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": ["Alice", "Bob"],
                "settings": {"num_sets": 1},
            },
            cookies=cookies,
        )
        game_id = game_resp.json()["id"]

        await client.post(f"/api/game/{game_id}/end", cookies=cookies)

        # Active game should return 404
        resp = await client.get(
            f"/api/game/active/{pg['id']}",
            cookies=cookies,
        )
        assert resp.status_code == 404


class TestCRUDCompleteness:
    """Full CRUD coverage for all entities with real data."""

    async def test_playground_full_lifecycle(self, client: AsyncClient):
        """Create → auth → get → verify all fields present."""
        # Create
        create_resp = await client.post(
            "/api/playground",
            json={
                "name": "CRUD Lifecycle",
                "pin": "9876",
                "players": ["Rahul", "Priya", "Amit", "Neha"],
            },
        )
        assert create_resp.status_code == 201
        pg = create_resp.json()
        assert pg["name"] == "CRUD Lifecycle"
        assert len(pg["share_code"]) == 4
        assert pg["players"] == ["Rahul", "Priya", "Amit", "Neha"]
        assert "id" in pg

        # Auth
        auth_resp = await client.post(
            "/api/playground/auth",
            json={
                "name": "CRUD Lifecycle",
                "pin": "9876",
            },
        )
        assert auth_resp.status_code == 200
        cookies = {"scokeep_session": auth_resp.cookies.get("scokeep_session")}

        # Get
        get_resp = await client.get(
            f"/api/playground/{pg['share_code']}",
            cookies=cookies,
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "CRUD Lifecycle"
        assert get_resp.json()["players"] == ["Rahul", "Priya", "Amit", "Neha"]

    async def test_game_full_lifecycle(self, client: AsyncClient):
        """Create game → bid → play → score → scoreboard → next round → end."""
        pg, cookies = await _setup(client, "Game CRUD")
        game_resp = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": ["Alice", "Bob", "Charlie"],
                "settings": {"num_sets": 1, "mode": "rookie", "must_lose": True},
            },
            cookies=cookies,
        )
        assert game_resp.status_code == 201
        game = game_resp.json()
        game_id = game["id"]
        assert game["phase"] == "bidding"
        assert game["current_round"] == 1
        assert game["total_rounds"] == 8
        assert game["players"] == ["Alice", "Bob", "Charlie"]

        # Full round: bid → confirm → play → hands → score
        for i, bid in enumerate([2, 3, 1]):
            r = await client.post(
                f"/api/game/{game_id}/bid",
                json={
                    "player_index": i,
                    "value": bid,
                },
                cookies=cookies,
            )
            assert r.status_code == 200

        r = await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
        assert r.status_code == 200

        r = await client.post(
            f"/api/game/{game_id}/enter-round-end",
            cookies=cookies,
        )
        assert r.status_code == 200

        for i, hands in enumerate([2, 3, 3]):
            r = await client.post(
                f"/api/game/{game_id}/hands",
                json={
                    "player_index": i,
                    "value": hands,
                },
                cookies=cookies,
            )
            assert r.status_code == 200

        r = await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)
        assert r.status_code == 200
        scores = r.json()["scores"]
        # Alice bid 2 got 2 → 20, Bob bid 3 got 3 → 30, Charlie bid 1 got 3 → -11
        assert scores == {"0": 20, "1": 30, "2": -11}

        # Scoreboard
        r = await client.get(f"/api/game/{game_id}/scoreboard", cookies=cookies)
        assert r.status_code == 200
        assert r.json()["totals"] == {"0": 20, "1": 30, "2": -11}

        # History
        r = await client.get(f"/api/game/{game_id}/history", cookies=cookies)
        assert r.status_code == 200

        # Next round
        r = await client.post(
            f"/api/game/{game_id}/next-round",
            cookies=cookies,
        )
        assert r.status_code == 200
        assert r.json()["current_round"] == 2
        assert r.json()["dealer_index"] == 1

        # End game
        r = await client.post(f"/api/game/{game_id}/end", cookies=cookies)
        assert r.status_code == 200
        assert r.json()["status"] == "finished"
        assert r.json()["phase"] == "final"

    async def test_round_full_lifecycle_with_undo(self, client: AsyncClient):
        """Score a round → undo → verify round is reverted."""
        pg, cookies = await _setup(client, "Round CRUD")
        game_resp = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": ["Alice", "Bob"],
                "settings": {"num_sets": 1},
            },
            cookies=cookies,
        )
        game_id = game_resp.json()["id"]

        # Complete round 1
        for i, bid in enumerate([3, 2]):
            await client.post(
                f"/api/game/{game_id}/bid",
                json={
                    "player_index": i,
                    "value": bid,
                },
                cookies=cookies,
            )
        await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
        await client.post(
            f"/api/game/{game_id}/enter-round-end",
            cookies=cookies,
        )
        for i, hands in enumerate([3, 5]):
            await client.post(
                f"/api/game/{game_id}/hands",
                json={
                    "player_index": i,
                    "value": hands,
                },
                cookies=cookies,
            )
        await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)

        # Verify scoreboard shows scores
        r = await client.get(f"/api/game/{game_id}/scoreboard", cookies=cookies)
        assert r.json()["totals"]["0"] == 30  # bid 3 got 3 → 30

        # Undo
        r = await client.post(f"/api/game/{game_id}/undo", cookies=cookies)
        assert r.status_code == 200
        assert r.json()["status"] == "undone"

        # Verify scoreboard is now empty
        r = await client.get(f"/api/game/{game_id}/scoreboard", cookies=cookies)
        assert r.json()["totals"] == {"0": 0, "1": 0}
