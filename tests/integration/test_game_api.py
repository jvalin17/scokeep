"""Integration tests for game API endpoints.

Tests game creation, state retrieval, and early ending.
"""

from httpx import AsyncClient


async def _create_authenticated_playground(client: AsyncClient) -> dict:
    """Helper: create playground and authenticate, return playground data + cookies."""
    create_response = await client.post("/api/playground", json={
        "name": "Game Test Group",
        "pin": "1234",
        "players": ["Alice", "Bob", "Charlie"],
    })
    playground = create_response.json()

    auth_response = await client.post("/api/playground/auth", json={
        "name": "Game Test Group",
        "pin": "1234",
    })
    cookies = {"scokeep_session": auth_response.cookies.get("scokeep_session")}
    return {**playground, "cookies": cookies}


class TestCreateGame:

    async def test_create_game_returns_201(self, client: AsyncClient):
        pg = await _create_authenticated_playground(client)

        response = await client.post("/api/game", json={
            "playground_id": pg["id"],
            "players": ["Alice", "Bob", "Charlie"],
        }, cookies=pg["cookies"])

        assert response.status_code == 201
        body = response.json()
        assert body["players"] == ["Alice", "Bob", "Charlie"]
        assert body["current_round"] == 1
        assert body["phase"] == "bidding"
        assert body["total_rounds"] == 24  # default 3 sets
        assert body["status"] == "active"

    async def test_create_game_with_custom_settings(self, client: AsyncClient):
        pg = await _create_authenticated_playground(client)

        response = await client.post("/api/game", json={
            "playground_id": pg["id"],
            "players": ["Alice", "Bob"],
            "settings": {"mode": "friendly", "num_sets": 1, "must_lose": True},
        }, cookies=pg["cookies"])

        assert response.status_code == 201
        body = response.json()
        assert body["settings"]["mode"] == "friendly"
        assert body["settings"]["must_lose"] is True
        assert body["total_rounds"] == 8

    async def test_create_game_needs_auth(self, client: AsyncClient):
        response = await client.post("/api/game", json={
            "playground_id": 1,
            "players": ["A", "B"],
        })

        assert response.status_code == 401

    async def test_create_game_too_few_players_returns_422(self, client: AsyncClient):
        pg = await _create_authenticated_playground(client)

        response = await client.post("/api/game", json={
            "playground_id": pg["id"],
            "players": ["Alice"],  # min 2
        }, cookies=pg["cookies"])

        assert response.status_code == 422


class TestGetGame:

    async def test_get_game_returns_state(self, client: AsyncClient):
        pg = await _create_authenticated_playground(client)
        create_response = await client.post("/api/game", json={
            "playground_id": pg["id"],
            "players": ["Alice", "Bob", "Charlie"],
        }, cookies=pg["cookies"])
        game_id = create_response.json()["id"]

        response = await client.get(f"/api/game/{game_id}", cookies=pg["cookies"])

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == game_id
        assert body["phase"] == "bidding"

    async def test_get_nonexistent_game_returns_404(self, client: AsyncClient):
        pg = await _create_authenticated_playground(client)

        response = await client.get("/api/game/9999", cookies=pg["cookies"])
        assert response.status_code == 404


class TestEndGame:

    async def test_end_game_sets_finished(self, client: AsyncClient):
        pg = await _create_authenticated_playground(client)
        create_response = await client.post("/api/game", json={
            "playground_id": pg["id"],
            "players": ["Alice", "Bob"],
        }, cookies=pg["cookies"])
        game_id = create_response.json()["id"]

        response = await client.post(
            f"/api/game/{game_id}/end", cookies=pg["cookies"]
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "finished"
        assert body["phase"] == "final"

    async def test_end_game_during_playing_phase(self, client: AsyncClient):
        """End game should work from any phase including playing."""
        pg = await _create_authenticated_playground(client)
        create_response = await client.post("/api/game", json={
            "playground_id": pg["id"],
            "players": ["Alice", "Bob"],
        }, cookies=pg["cookies"])
        game_id = create_response.json()["id"]

        # Submit bids and start round to get to playing phase
        await client.post(f"/api/game/{game_id}/bid", json={
            "player_index": 0, "value": 2,
        }, cookies=pg["cookies"])
        await client.post(f"/api/game/{game_id}/bid", json={
            "player_index": 1, "value": 3,
        }, cookies=pg["cookies"])
        await client.post(f"/api/game/{game_id}/start-round", cookies=pg["cookies"])

        # Verify we're in playing phase
        game = await client.get(f"/api/game/{game_id}", cookies=pg["cookies"])
        assert game.json()["phase"] == "playing"

        # End game from playing phase
        response = await client.post(
            f"/api/game/{game_id}/end", cookies=pg["cookies"]
        )
        assert response.status_code == 200
        assert response.json()["status"] == "finished"

    async def test_end_already_finished_returns_409(self, client: AsyncClient):
        pg = await _create_authenticated_playground(client)
        create_response = await client.post("/api/game", json={
            "playground_id": pg["id"],
            "players": ["Alice", "Bob"],
        }, cookies=pg["cookies"])
        game_id = create_response.json()["id"]

        await client.post(f"/api/game/{game_id}/end", cookies=pg["cookies"])
        response = await client.post(
            f"/api/game/{game_id}/end", cookies=pg["cookies"]
        )

        assert response.status_code == 409
