"""Integration tests for scoreboard and undo API endpoints."""

from httpx import AsyncClient


async def _play_round(client: AsyncClient, game_id: int, cookies: dict, bids: list, hands: list):
    """Helper: play a full round — bid, confirm, enter round end, hands, score."""
    for i, bid in enumerate(bids):
        await client.post(
            f"/api/game/{game_id}/bid",
            json={"player_index": i, "value": bid},
            cookies=cookies,
        )
    await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
    await client.post(f"/api/game/{game_id}/enter-round-end", cookies=cookies)
    for i, hand in enumerate(hands):
        await client.post(
            f"/api/game/{game_id}/hands",
            json={"player_index": i, "value": hand},
            cookies=cookies,
        )
    return await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)


async def _setup_game_with_rounds(client: AsyncClient):
    """Helper: create playground, auth, game, play 2 rounds. Return game_id + cookies."""
    await client.post("/api/playground", json={
        "name": "Scoreboard Test",
        "pin": "1234",
        "players": ["Alice", "Bob", "Charlie"],
    })
    auth = await client.post("/api/playground/auth", json={
        "name": "Scoreboard Test", "pin": "1234",
    })
    cookies = {"scokeep_session": auth.cookies.get("scokeep_session")}
    pg = auth.json()

    game_resp = await client.post("/api/game", json={
        "playground_id": pg["id"],
        "players": ["Alice", "Bob", "Charlie"],
        "settings": {"num_sets": 1},
    }, cookies=cookies)
    game_id = game_resp.json()["id"]

    # Round 1: bids=[2,0,1], hands=[2,0,1] → scores=[20,10,11]
    await _play_round(client, game_id, cookies, [2, 0, 1], [2, 0, 1])
    # Round 2: bids=[0,3,0], hands=[1,3,0] → scores=[-10,30,10]
    await _play_round(client, game_id, cookies, [0, 3, 0], [1, 3, 0])

    return game_id, cookies


class TestGetScoreboard:

    async def test_scoreboard_returns_totals(self, client: AsyncClient):
        game_id, cookies = await _setup_game_with_rounds(client)

        response = await client.get(
            f"/api/game/{game_id}/scoreboard", cookies=cookies,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["totals"] == {"0": 10, "1": 40, "2": 21}
        assert len(body["rounds"]) == 2


class TestGetHistory:

    async def test_history_returns_bid_vs_actual(self, client: AsyncClient):
        game_id, cookies = await _setup_game_with_rounds(client)

        response = await client.get(
            f"/api/game/{game_id}/history", cookies=cookies,
        )

        assert response.status_code == 200
        history = response.json()
        assert len(history) == 2
        assert history[0]["bids"] == {"0": 2, "1": 0, "2": 1}
        assert history[0]["hands_won"] == {"0": 2, "1": 0, "2": 1}


class TestUndo:

    async def test_undo_decrements_round(self, client: AsyncClient):
        game_id, cookies = await _setup_game_with_rounds(client)

        response = await client.post(
            f"/api/game/{game_id}/undo", cookies=cookies,
        )

        assert response.status_code == 200

        # Game should be back at round 2
        game_resp = await client.get(f"/api/game/{game_id}", cookies=cookies)
        assert game_resp.json()["current_round"] == 2

    async def test_undo_updates_scoreboard(self, client: AsyncClient):
        game_id, cookies = await _setup_game_with_rounds(client)

        await client.post(f"/api/game/{game_id}/undo", cookies=cookies)

        scoreboard = await client.get(
            f"/api/game/{game_id}/scoreboard", cookies=cookies,
        )
        body = scoreboard.json()
        # Only round 1 scores remain: 20, 10, 11
        assert body["totals"] == {"0": 20, "1": 10, "2": 11}
