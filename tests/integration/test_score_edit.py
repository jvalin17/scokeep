"""Integration tests for score correction endpoint."""

from httpx import AsyncClient

from app.config import settings

settings.admin_key = "test-admin-secret"


async def _setup(client: AsyncClient):
    """Create playground, auth, play a game with 1 round, return context."""
    await client.post("/api/playground", json={
        "name": "Score Edit Test", "pin": "1234",
        "players": ["Alice", "Bob"],
    })
    auth = await client.post("/api/playground/auth", json={
        "name": "Score Edit Test", "pin": "1234",
    })
    cookies = {"scokeep_session": auth.cookies.get("scokeep_session")}
    pg = auth.json()

    # Create and play 1-round game
    game_resp = await client.post("/api/game", json={
        "playground_id": pg["id"],
        "players": ["Alice", "Bob"],
        "settings": {"num_sets": 1},
    }, cookies=cookies)
    game_id = game_resp.json()["id"]

    # Bid
    await client.post(f"/api/game/{game_id}/bid", json={
        "player_index": 0, "value": 2,
    }, cookies=cookies)
    await client.post(f"/api/game/{game_id}/bid", json={
        "player_index": 1, "value": 3,
    }, cookies=cookies)
    await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
    await client.post(f"/api/game/{game_id}/enter-round-end", cookies=cookies)

    # Hands
    await client.post(f"/api/game/{game_id}/hands", json={
        "player_index": 0, "value": 2,
    }, cookies=cookies)
    await client.post(f"/api/game/{game_id}/hands", json={
        "player_index": 1, "value": 1,
    }, cookies=cookies)

    # Score and end
    await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)
    await client.post(f"/api/game/{game_id}/end", cookies=cookies)

    return game_id, cookies


class TestScoreCorrection:
    """PATCH /api/game/{game_id}/round/{round_num}/score — admin key required."""

    async def test_correct_score_with_admin_key(self, client: AsyncClient):
        game_id, cookies = await _setup(client)

        resp = await client.patch(
            f"/api/game/{game_id}/round/1/score",
            json={"player_index": 0, "score": 99},
            headers={"X-Admin-Key": "test-admin-secret"},
            cookies=cookies,
        )
        assert resp.status_code == 200
        assert resp.json()["updated_score"] == 99

        # Verify via scoreboard
        sb = await client.get(
            f"/api/game/{game_id}/scoreboard", cookies=cookies,
        )
        assert sb.json()["rounds"][0]["scores"]["0"] == 99

    async def test_rejects_without_admin_key(self, client: AsyncClient):
        game_id, cookies = await _setup(client)

        resp = await client.patch(
            f"/api/game/{game_id}/round/1/score",
            json={"player_index": 0, "score": 99},
            cookies=cookies,
        )
        assert resp.status_code == 403

    async def test_rejects_wrong_admin_key(self, client: AsyncClient):
        game_id, cookies = await _setup(client)

        resp = await client.patch(
            f"/api/game/{game_id}/round/1/score",
            json={"player_index": 0, "score": 99},
            headers={"X-Admin-Key": "wrong"},
            cookies=cookies,
        )
        assert resp.status_code == 403

    async def test_rejects_invalid_round(self, client: AsyncClient):
        game_id, cookies = await _setup(client)

        resp = await client.patch(
            f"/api/game/{game_id}/round/999/score",
            json={"player_index": 0, "score": 10},
            headers={"X-Admin-Key": "test-admin-secret"},
            cookies=cookies,
        )
        assert resp.status_code == 404

    async def test_rejects_invalid_player_index(self, client: AsyncClient):
        game_id, cookies = await _setup(client)

        resp = await client.patch(
            f"/api/game/{game_id}/round/1/score",
            json={"player_index": 5, "score": 10},
            headers={"X-Admin-Key": "test-admin-secret"},
            cookies=cookies,
        )
        assert resp.status_code == 400
