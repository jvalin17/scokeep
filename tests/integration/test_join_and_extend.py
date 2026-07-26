"""Tests for join-without-PIN and extend-at-set-end features.

Covers requirements:
- Join live game by share code (no PIN needed for active game) — req line 94
- Extend at set end (add another set) — req line 134
"""

from httpx import AsyncClient


async def _setup(client: AsyncClient, name: str = "Join Test"):
    """Create playground, auth, return (playground, cookies)."""
    await client.post("/api/playground", json={
        "name": name, "pin": "1234",
        "players": ["Alice", "Bob", "Charlie"],
    })
    auth = await client.post("/api/playground/auth", json={
        "name": name, "pin": "1234",
    })
    cookies = {"scokeep_session": auth.cookies.get("scokeep_session")}
    return auth.json(), cookies


async def _complete_round(client: AsyncClient, game_id: int, cookies: dict):
    """Helper: complete one full round (bid → play → hands → score)."""
    for i, bid in enumerate([2, 3, 1]):
        await client.post(f"/api/game/{game_id}/bid", json={
            "player_index": i, "value": bid,
        }, cookies=cookies)
    await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
    await client.post(
        f"/api/game/{game_id}/enter-round-end", cookies=cookies,
    )
    for i, hands in enumerate([2, 3, 3]):
        await client.post(f"/api/game/{game_id}/hands", json={
            "player_index": i, "value": hands,
        }, cookies=cookies)
    await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)


class TestJoinLiveGame:
    """POST /api/playground/join/{share_code} — no PIN needed."""

    async def test_join_with_active_game_succeeds(self, client: AsyncClient):
        """Can join by share code when there's an active game."""
        pg, cookies = await _setup(client, "Join Active")

        # Create a game
        await client.post("/api/game", json={
            "playground_id": pg["id"],
            "players": ["Alice", "Bob", "Charlie"],
            "settings": {"num_sets": 1},
        }, cookies=cookies)

        # Join without PIN — just share code
        resp = await client.post(f"/api/playground/join/{pg['share_code']}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Join Active"
        assert "scokeep_session" in resp.cookies

    async def test_join_without_active_game_returns_404(
        self, client: AsyncClient,
    ):
        """Cannot join by share code when there's no active game."""
        pg, cookies = await _setup(client, "Join No Active")

        resp = await client.post(f"/api/playground/join/{pg['share_code']}")
        assert resp.status_code == 404
        assert "No active game" in resp.json()["detail"]

    async def test_join_invalid_share_code_returns_404(
        self, client: AsyncClient,
    ):
        """Invalid share code returns 404."""
        resp = await client.post("/api/playground/join/ZZZZ")
        assert resp.status_code == 404


class TestExtendGame:
    """POST /api/game/{id}/extend — add another set at set end."""

    async def test_extend_adds_8_rounds(self, client: AsyncClient):
        """Extending adds 8 rounds (1 set) to total_rounds."""
        pg, cookies = await _setup(client, "Extend Test")

        game_resp = await client.post("/api/game", json={
            "playground_id": pg["id"],
            "players": ["Alice", "Bob", "Charlie"],
            "settings": {"num_sets": 1},
        }, cookies=cookies)
        game_id = game_resp.json()["id"]
        assert game_resp.json()["total_rounds"] == 8

        # Complete a round to get to scoreboard
        await _complete_round(client, game_id, cookies)

        # Extend
        resp = await client.post(
            f"/api/game/{game_id}/extend", cookies=cookies,
        )
        assert resp.status_code == 200
        assert resp.json()["total_rounds"] == 16  # 8 + 8

    async def test_extend_only_from_scoreboard(self, client: AsyncClient):
        """Cannot extend during bidding or play phase."""
        pg, cookies = await _setup(client, "Extend Phase Test")

        game_resp = await client.post("/api/game", json={
            "playground_id": pg["id"],
            "players": ["Alice", "Bob", "Charlie"],
            "settings": {"num_sets": 1},
        }, cookies=cookies)
        game_id = game_resp.json()["id"]

        # Try to extend during bidding — should fail
        resp = await client.post(
            f"/api/game/{game_id}/extend", cookies=cookies,
        )
        assert resp.status_code == 409
        assert "scoreboard" in resp.json()["detail"]

    async def test_cannot_extend_finished_game(self, client: AsyncClient):
        """Cannot extend a finished game."""
        pg, cookies = await _setup(client, "Extend Finished Test")

        game_resp = await client.post("/api/game", json={
            "playground_id": pg["id"],
            "players": ["Alice", "Bob"],
            "settings": {"num_sets": 1},
        }, cookies=cookies)
        game_id = game_resp.json()["id"]

        await client.post(f"/api/game/{game_id}/end", cookies=cookies)

        resp = await client.post(
            f"/api/game/{game_id}/extend", cookies=cookies,
        )
        assert resp.status_code == 409
