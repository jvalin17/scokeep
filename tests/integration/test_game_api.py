"""Integration tests for game API endpoints.

Tests game creation, state retrieval, early ending, and cascade deletion.
"""

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def _create_authenticated_playground(client: AsyncClient) -> dict:
    """Helper: create playground and authenticate, return playground data + cookies."""
    create_response = await client.post(
        "/api/playground",
        json={
            "name": "Game Test Group",
            "pin": "1234",
            "players": ["Alice", "Bob", "Charlie"],
        },
    )
    playground = create_response.json()

    auth_response = await client.post(
        "/api/playground/auth",
        json={
            "name": "Game Test Group",
            "pin": "1234",
        },
    )
    cookies = {"scokeep_session": auth_response.cookies.get("scokeep_session")}
    return {**playground, "cookies": cookies}


class TestCreateGame:
    async def test_create_game_returns_201(self, client: AsyncClient):
        pg = await _create_authenticated_playground(client)

        response = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": ["Alice", "Bob", "Charlie"],
            },
            cookies=pg["cookies"],
        )

        assert response.status_code == 201
        body = response.json()
        assert body["players"] == ["Alice", "Bob", "Charlie"]
        assert body["current_round"] == 1
        assert body["phase"] == "bidding"
        assert body["total_rounds"] == 24  # default 3 sets
        assert body["status"] == "active"

    async def test_create_game_with_custom_settings(self, client: AsyncClient):
        pg = await _create_authenticated_playground(client)

        response = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": ["Alice", "Bob"],
                "settings": {"mode": "friendly", "num_sets": 1, "must_lose": True},
            },
            cookies=pg["cookies"],
        )

        assert response.status_code == 201
        body = response.json()
        assert body["settings"]["mode"] == "friendly"
        assert body["settings"]["must_lose"] is True
        assert body["total_rounds"] == 8

    async def test_create_game_needs_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/game",
            json={
                "playground_id": 1,
                "players": ["A", "B"],
            },
        )

        assert response.status_code == 401

    async def test_create_game_too_few_players_returns_422(self, client: AsyncClient):
        pg = await _create_authenticated_playground(client)

        response = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": ["Alice"],  # min 2
            },
            cookies=pg["cookies"],
        )

        assert response.status_code == 422

    async def test_create_game_rejects_invalid_formula(self, client: AsyncClient):
        """scoring_formula must be one of the allowed values."""
        pg = await _create_authenticated_playground(client)

        response = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": ["Alice", "Bob"],
                "settings": {"scoring_formula": "evil"},
            },
            cookies=pg["cookies"],
        )

        assert response.status_code == 422, (
            f"Expected 422 for invalid formula, got {response.status_code}"
        )


class TestGetGame:
    async def test_get_game_returns_state(self, client: AsyncClient):
        pg = await _create_authenticated_playground(client)
        create_response = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": ["Alice", "Bob", "Charlie"],
            },
            cookies=pg["cookies"],
        )
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
        create_response = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": ["Alice", "Bob"],
            },
            cookies=pg["cookies"],
        )
        game_id = create_response.json()["id"]

        # /end transitions to review phase (status stays active)
        response = await client.post(f"/api/game/{game_id}/end", cookies=pg["cookies"])
        assert response.status_code == 200
        body = response.json()
        assert body["phase"] == "review"
        assert body["status"] == "active"

        # confirm-final finishes it
        response = await client.post(f"/api/game/{game_id}/confirm-final", cookies=pg["cookies"])
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "finished"
        assert body["phase"] == "final"

    async def test_end_game_during_playing_phase(self, client: AsyncClient):
        """End game should work from any phase including playing."""
        pg = await _create_authenticated_playground(client)
        create_response = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": ["Alice", "Bob"],
            },
            cookies=pg["cookies"],
        )
        game_id = create_response.json()["id"]

        # Submit bids and start round to get to playing phase
        await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 0,
                "value": 2,
            },
            cookies=pg["cookies"],
        )
        await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 1,
                "value": 3,
            },
            cookies=pg["cookies"],
        )
        await client.post(f"/api/game/{game_id}/start-round", cookies=pg["cookies"])

        # Verify we're in playing phase
        game = await client.get(f"/api/game/{game_id}", cookies=pg["cookies"])
        assert game.json()["phase"] == "playing"

        # End game from playing → review phase
        response = await client.post(f"/api/game/{game_id}/end", cookies=pg["cookies"])
        assert response.status_code == 200
        assert response.json()["phase"] == "review"
        assert response.json()["status"] == "active"

        # confirm-final finishes it
        response = await client.post(f"/api/game/{game_id}/confirm-final", cookies=pg["cookies"])
        assert response.status_code == 200
        assert response.json()["status"] == "finished"

    async def test_end_already_finished_returns_409(self, client: AsyncClient):
        pg = await _create_authenticated_playground(client)
        create_response = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": ["Alice", "Bob"],
            },
            cookies=pg["cookies"],
        )
        game_id = create_response.json()["id"]

        await client.post(f"/api/game/{game_id}/end", cookies=pg["cookies"])
        await client.post(f"/api/game/{game_id}/confirm-final", cookies=pg["cookies"])
        response = await client.post(f"/api/game/{game_id}/end", cookies=pg["cookies"])

        assert response.status_code == 409


class TestGameWithCustomRoundsPerSet:
    """Games with different rounds_per_set based on player count."""

    async def test_7_players_max_7_cards(self, client: AsyncClient):
        """7 players can play with up to 7 cards per round (52/7=7)."""
        pg = await _create_authenticated_playground(client)
        players = ["Ana", "Ben", "Cal", "Dan", "Eve", "Fay", "Gil"]
        resp = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": players,
                "settings": {"rounds_per_set": 7},
            },
            cookies=pg["cookies"],
        )
        assert resp.status_code == 201
        game = resp.json()
        assert game["settings"]["rounds_per_set"] == 7
        assert game["total_rounds"] == 21  # 3 sets × 7

    async def test_8_players_max_6_cards(self, client: AsyncClient):
        """8 players can play with up to 6 cards per round (52/8=6)."""
        pg = await _create_authenticated_playground(client)
        players = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]
        resp = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": players,
                "settings": {"rounds_per_set": 6},
            },
            cookies=pg["cookies"],
        )
        assert resp.status_code == 201
        assert resp.json()["settings"]["rounds_per_set"] == 6

    async def test_custom_5_rounds_per_set(self, client: AsyncClient):
        """Players can choose fewer rounds (e.g., 5) for shorter games."""
        pg = await _create_authenticated_playground(client)
        resp = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": ["Alice", "Bob", "Charlie"],
                "settings": {"rounds_per_set": 5},
            },
            cookies=pg["cookies"],
        )
        assert resp.status_code == 201
        assert resp.json()["total_rounds"] == 15  # 3 sets × 5


class TestDeleteGameCascadesRounds:
    """L11: Deleting a game must cascade-delete its rounds via FK constraint."""

    async def test_delete_game_cascades_rounds(self, client: AsyncClient, db_session: AsyncSession):
        """Delete a game row → its rounds are also deleted by ON DELETE CASCADE."""
        # Enable FK enforcement (SQLite requires this explicitly)
        await db_session.execute(text("PRAGMA foreign_keys = ON"))

        # Arrange: create a game with a round via API
        pg = await _create_authenticated_playground(client)
        create_resp = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": ["Alice", "Bob"],
            },
            cookies=pg["cookies"],
        )
        game_id = create_resp.json()["id"]

        # Submit bids to create a round row
        await client.post(
            f"/api/game/{game_id}/bid",
            json={"player_index": 0, "value": 1},
            cookies=pg["cookies"],
        )

        # Verify round exists
        rounds_before = await db_session.execute(
            text("SELECT COUNT(*) FROM round WHERE game_id = :gid"),
            {"gid": game_id},
        )
        assert rounds_before.scalar() >= 1, "Round should exist before delete"

        # Act: delete the game row directly
        await db_session.execute(text("DELETE FROM game WHERE id = :gid"), {"gid": game_id})
        await db_session.commit()

        # Assert: rounds are gone (CASCADE)
        rounds_after = await db_session.execute(
            text("SELECT COUNT(*) FROM round WHERE game_id = :gid"),
            {"gid": game_id},
        )
        assert rounds_after.scalar() == 0, "Rounds should be cascade-deleted when game is deleted"
