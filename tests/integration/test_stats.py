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
        assert body["head_to_head"] == []

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

    async def test_stats_head_to_head(self, client: AsyncClient):
        """Head-to-head records track wins between pairs."""
        pg, cookies = await _setup(client, "H2H Stats")

        # Game 1: Alice wins (bid 3 get 3 → 30, Bob bid 1 get 1 → 11)
        await _play_full_game(
            client, pg["id"], cookies,
            players=["Alice", "Bob"],
            bids=[3, 1], hands=[3, 5],
        )

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        h2h = resp.json()["head_to_head"]
        assert len(h2h) == 1
        record = h2h[0]["record"]
        assert record["games"] == 1
        assert record["Alice"] == 1  # Alice won
        assert record["Bob"] == 0

    async def test_stats_requires_auth(self, client: AsyncClient):
        """Stats endpoint requires authentication."""
        pg, cookies = await _setup(client, "Auth Stats")

        # Use explicit empty cookies to avoid httpx cookie persistence
        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats",
            cookies={"scokeep_session": ""},
        )
        assert resp.status_code == 401
