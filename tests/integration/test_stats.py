"""Integration tests for playground stats/analytics endpoint.

Tests GET /api/playground/{share_code}/stats with real game data.
Verifies leaderboard, bid accuracy, head-to-head, and game history.
"""

from httpx import AsyncClient


async def _setup(client: AsyncClient, name: str = "Stats Test"):
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


async def _play_full_game(
    client: AsyncClient, pg_id: int, cookies: dict,
    players: list[str], bids: list[int], hands: list[int],
):
    """Create game, play 1 round, end game. Return game dict."""
    game_resp = await client.post("/api/game", json={
        "playground_id": pg_id,
        "players": players,
        "settings": {"num_sets": 1},
    }, cookies=cookies)
    game_id = game_resp.json()["id"]

    # Bid
    for i, bid in enumerate(bids):
        await client.post(f"/api/game/{game_id}/bid", json={
            "player_index": i, "value": bid,
        }, cookies=cookies)

    # Start round
    await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
    await client.post(
        f"/api/game/{game_id}/enter-round-end", cookies=cookies,
    )

    # Hands
    for i, hand in enumerate(hands):
        await client.post(f"/api/game/{game_id}/hands", json={
            "player_index": i, "value": hand,
        }, cookies=cookies)

    # Score + end
    await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)
    await client.post(f"/api/game/{game_id}/end", cookies=cookies)
    return game_resp.json()


class TestPlaygroundStats:
    """GET /api/playground/{share_code}/stats — analytics endpoint."""

    async def test_stats_with_no_games_returns_empty(
        self, client: AsyncClient,
    ):
        """Empty playground returns zeroed stats."""
        pg, cookies = await _setup(client, "Empty Stats")

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_games"] == 0
        assert body["leaderboard"] == []
        assert body["game_history"] == []
        assert body["trends"] == []

    async def test_stats_after_one_game(self, client: AsyncClient):
        """Stats after 1 finished game show correct leaderboard."""
        pg, cookies = await _setup(client, "One Game Stats")

        # Alice bids 2 gets 2 → 20, Bob bids 3 gets 3 → 30, Charlie bids 1 gets 3 → -11
        await _play_full_game(
            client, pg["id"], cookies,
            players=["Alice", "Bob", "Charlie"],
            bids=[2, 3, 1], hands=[2, 3, 3],
        )

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_games"] == 1

        # Leaderboard should have Bob first (winner with 30 pts)
        lb = body["leaderboard"]
        assert len(lb) == 3
        assert lb[0]["name"] == "Bob"
        assert lb[0]["wins"] == 1
        assert lb[0]["total_score"] == 30

        # Game history
        assert len(body["game_history"]) == 1
        assert body["game_history"][0]["winner"] == "Bob"

    async def test_stats_bid_accuracy(self, client: AsyncClient):
        """Bid accuracy is calculated correctly."""
        pg, cookies = await _setup(client, "Accuracy Stats")

        # Alice bids 2 gets 2 (hit), Bob bids 3 gets 1 (miss)
        await _play_full_game(
            client, pg["id"], cookies,
            players=["Alice", "Bob"],
            bids=[2, 3], hands=[2, 6],
        )

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        lb = resp.json()["leaderboard"]
        alice = next(p for p in lb if p["name"] == "Alice")
        bob = next(p for p in lb if p["name"] == "Bob")

        assert alice["bid_accuracy"] == 100  # 1/1 bids hit
        assert bob["bid_accuracy"] == 0     # 0/1 bids hit

    async def test_trends_overbid_underbid(self, client: AsyncClient):
        """Trends track overbid/underbid counts per player."""
        pg, cookies = await _setup(client, "Trends OB/UB")

        # Alice bids 3, gets 1 (overbid). Bob bids 1, gets 7 (underbid).
        await _play_full_game(
            client, pg["id"], cookies,
            players=["Alice", "Bob"],
            bids=[3, 1], hands=[1, 7],
        )

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        trends = resp.json()["trends"]
        alice = next(t for t in trends if t["name"] == "Alice")
        bob = next(t for t in trends if t["name"] == "Bob")

        assert alice["overbids"] == 1
        assert alice["underbids"] == 0
        assert bob["overbids"] == 0
        assert bob["underbids"] == 1

    async def test_trends_win_streaks(self, client: AsyncClient):
        """Trends track current and longest win streaks."""
        pg, cookies = await _setup(client, "Trends Streaks")

        # Alice wins 2 games in a row
        for _ in range(2):
            await _play_full_game(
                client, pg["id"], cookies,
                players=["Alice", "Bob"],
                bids=[3, 0], hands=[3, 5],  # Alice: +30, Bob: -10
            )

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        trends = resp.json()["trends"]
        alice = next(t for t in trends if t["name"] == "Alice")
        bob = next(t for t in trends if t["name"] == "Bob")

        assert alice["current_streak"] == 2
        assert alice["longest_streak"] == 2
        assert bob["current_streak"] == 0
        assert bob["longest_streak"] == 0

    async def test_clear_stats_deletes_finished_games(
        self, client: AsyncClient,
    ):
        """Clear stats removes all finished games but keeps active ones."""
        pg, cookies = await _setup(client, "Clear Stats")

        # Play and finish a game
        await _play_full_game(
            client, pg["id"], cookies,
            players=["Alice", "Bob"],
            bids=[2, 3], hands=[2, 6],
        )

        # Verify stats show 1 game
        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        assert resp.json()["total_games"] == 1

        # Clear stats
        resp = await client.delete(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        assert resp.status_code == 200
        assert resp.json()["deleted_games"] == 1

        # Stats should be empty now
        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        assert resp.json()["total_games"] == 0
        assert resp.json()["leaderboard"] == []

    async def test_clear_stats_keeps_active_game(
        self, client: AsyncClient,
    ):
        """Clear stats does not delete active (in-progress) games."""
        pg, cookies = await _setup(client, "Clear Active")

        # Create an active game (don't finish it)
        await client.post("/api/game", json={
            "playground_id": pg["id"],
            "players": ["Alice", "Bob"],
            "settings": {"num_sets": 1},
        }, cookies=cookies)

        # Clear stats — should delete 0 (only finished games)
        resp = await client.delete(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        assert resp.status_code == 200
        assert resp.json()["deleted_games"] == 0

    async def test_stats_requires_auth(self, client: AsyncClient):
        """Stats endpoint requires authentication."""
        pg, cookies = await _setup(client, "Auth Stats")

        # Use explicit empty cookies to avoid httpx cookie persistence
        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats",
            cookies={"scokeep_session": ""},
        )
        assert resp.status_code == 401
