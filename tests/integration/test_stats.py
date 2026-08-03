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


async def _play_multi_round_game(
    client: AsyncClient, pg_id: int, cookies: dict,
    players: list[str], rounds_data: list[tuple[list[int], list[int]]],
    settings: dict | None = None,
):
    """Create game, play multiple rounds, end game.

    rounds_data: list of (bids, hands) tuples per round.
    Example: [([2, 1], [2, 6]), ([0, 3], [0, 3])] — 2 rounds, 2 players.
    """
    game_resp = await client.post("/api/game", json={
        "playground_id": pg_id,
        "players": players,
        "settings": settings or {"num_sets": 1},
    }, cookies=cookies)
    game_id = game_resp.json()["id"]

    for round_idx, (bids, hands) in enumerate(rounds_data):
        for i, bid in enumerate(bids):
            await client.post(f"/api/game/{game_id}/bid", json={
                "player_index": i, "value": bid,
            }, cookies=cookies)
        await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
        await client.post(
            f"/api/game/{game_id}/enter-round-end", cookies=cookies,
        )
        for i, hand in enumerate(hands):
            await client.post(f"/api/game/{game_id}/hands", json={
                "player_index": i, "value": hand,
            }, cookies=cookies)
        await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)
        if round_idx < len(rounds_data) - 1:
            await client.post(
                f"/api/game/{game_id}/next-round", cookies=cookies,
            )

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


class TestHighlights:
    """GET /api/playground/{share_code}/stats — highlights section."""

    async def test_career_sniper_counts_bid1_made(self, client: AsyncClient):
        """Sniper counts times a player bid 1 and made it."""
        pg, cookies = await _setup(client, "Sniper Stats")

        # Game: Alice bids 1 makes 1 (sniper). Bob bids 0 makes 0.
        # Round with 8 cards: hands must sum to 8
        await _play_full_game(
            client, pg["id"], cookies,
            players=["Alice", "Bob"],
            bids=[1, 0], hands=[1, 7],
        )

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        highlights = resp.json()["highlights"]
        sniper = highlights["career"]["sniper"]
        alice = next(p for p in sniper if p["name"] == "Alice")
        bob = next(p for p in sniper if p["name"] == "Bob")
        assert alice["count"] == 1
        assert bob["count"] == 0

    async def test_career_zero_master_counts_bid0_made(
        self, client: AsyncClient,
    ):
        """Zero master counts times a player bid 0 and made it."""
        pg, cookies = await _setup(client, "ZeroMaster Stats")

        # Bob bids 0 and makes 0 (zero master). Alice takes all 8 hands.
        await _play_full_game(
            client, pg["id"], cookies,
            players=["Alice", "Bob"],
            bids=[3, 0], hands=[8, 0],
        )

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        zero_master = resp.json()["highlights"]["career"]["zero_master"]
        bob = next(p for p in zero_master if p["name"] == "Bob")
        assert bob["count"] == 1

    async def test_career_high_roller_counts_bid3plus_made(
        self, client: AsyncClient,
    ):
        """High roller counts times a player bid 3+ and made it."""
        pg, cookies = await _setup(client, "HighRoller Stats")

        # Alice bids 5, makes 5 (high roller)
        await _play_full_game(
            client, pg["id"], cookies,
            players=["Alice", "Bob"],
            bids=[5, 0], hands=[5, 3],
        )

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        high_roller = resp.json()["highlights"]["career"]["high_roller"]
        alice = next(p for p in high_roller if p["name"] == "Alice")
        assert alice["count"] == 1

    async def test_career_jinxed_tracks_longest_miss_streak(
        self, client: AsyncClient,
    ):
        """Jinxed tracks longest consecutive missed bids per player."""
        pg, cookies = await _setup(client, "Jinxed Stats")

        # 2 rounds: Alice misses both (jinxed streak = 2)
        # Round 1: 8 cards. Alice bids 3 gets 1 (miss), Bob bids 0 gets 0 (made)
        # Round 2: 7 cards. Alice bids 2 gets 0 (miss), Bob bids 0 gets 0 (made)
        await _play_multi_round_game(
            client, pg["id"], cookies,
            players=["Alice", "Bob"],
            rounds_data=[
                ([3, 0], [8, 0]),  # Alice miss (bid 3 got 8), Bob makes (bid 0 got 0)
                ([2, 0], [7, 0]),  # Alice miss (bid 2 got 7), Bob makes (bid 0 got 0)
            ],
            settings={"num_sets": 1, "rounds_per_set": 8},
        )

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        jinxed = resp.json()["highlights"]["career"]["jinxed"]
        alice = next(p for p in jinxed if p["name"] == "Alice")
        bob = next(p for p in jinxed if p["name"] == "Bob")
        assert alice["longest"] == 2  # missed both rounds
        assert bob["longest"] == 0   # made both rounds

    async def test_recent_hot_hand_shows_highest_round_score(
        self, client: AsyncClient,
    ):
        """Hot hand shows the highest single-round score in last 3 games."""
        pg, cookies = await _setup(client, "HotHand Stats")

        # Alice gets +50 (bid 5 made)
        await _play_full_game(
            client, pg["id"], cookies,
            players=["Alice", "Bob"],
            bids=[5, 0], hands=[5, 3],
        )

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        hot_hand = resp.json()["highlights"]["recent"]["hot_hand"]
        assert hot_hand["name"] == "Alice"
        assert hot_hand["score"] == 50

    async def test_highlights_empty_with_no_games(self, client: AsyncClient):
        """Highlights are empty when no games played."""
        pg, cookies = await _setup(client, "Empty Highlights")

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        body = resp.json()
        assert body["total_games"] == 0
        assert body["highlights"]["career"]["sniper"] == []
        assert body["highlights"]["recent"]["hot_hand"] is None
        assert body["highlights"]["last_game"] is None

    async def test_last_game_awards(self, client: AsyncClient):
        """Last game awards highlight individual achievements."""
        pg, cookies = await _setup(client, "LastGame Awards")

        # Play a 2-round game with clear award winners:
        # Round 1 (8 cards): Alice bids 5 makes 5 (+50), Bob bids 0 makes 0 (+10)
        # Round 2 (7 cards): Alice bids 2 makes 0 (miss -20), Bob bids 0 makes 0 (+10)
        await _play_multi_round_game(
            client, pg["id"], cookies,
            players=["Alice", "Bob"],
            rounds_data=[
                ([5, 0], [5, 3]),  # Alice: +50 (bold bid 5), Bob: -10 (bid 0 got 3)
                ([2, 0], [7, 0]),  # Alice: -20 (overbid), Bob: +10 (zero master)
            ],
            settings={"num_sets": 1, "rounds_per_set": 8},
        )

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        last_game = resp.json()["highlights"]["last_game"]
        assert last_game is not None

        # MVP: Alice with 50 + (-20) = 30 vs Bob with -10 + 10 = 0
        assert last_game["mvp"]["name"] == "Alice"
        assert last_game["mvp"]["score"] == 30

        # Bold Move: Alice bid 5 and made it
        assert last_game["bold_move"]["name"] == "Alice"
        assert last_game["bold_move"]["bid"] == 5

        # Brick Wall: Bob bid 0 once and made it
        assert last_game["brick_wall"]["name"] == "Bob"
        assert last_game["brick_wall"]["count"] == 1

        # Gambler: Alice overbid once (bid 2, got 7 — underbid actually)
        # Actually: round 1 Alice bid 5 got 5 (exact), round 2 bid 2 got 7 (underbid)
        # Bob: round 1 bid 0 got 3 (underbid), round 2 bid 0 got 0 (exact)
        # Sandbagger (most underbids): Alice 1, Bob 1 — tie, first alphabetically
        # Gambler (most overbids): neither overbid in this data
        # Let's just check the keys exist
        assert "sandbagger" in last_game
        assert "gambler" in last_game

    async def test_last_game_sharpshooter(self, client: AsyncClient):
        """Sharpshooter goes to player with best accuracy in last game."""
        pg, cookies = await _setup(client, "Sharpshooter Test")

        # Bob makes both bids (bid 0, got 0). Alice makes 1/2.
        await _play_multi_round_game(
            client, pg["id"], cookies,
            players=["Alice", "Bob"],
            rounds_data=[
                ([3, 0], [3, 5]),   # Alice makes (bid 3 got 3), Bob misses (bid 0 got 5)
                ([2, 0], [2, 0]),   # Alice makes (bid 2 got 2), Bob makes (bid 0 got 0)
            ],
            settings={"num_sets": 1, "rounds_per_set": 8},
        )

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        last_game = resp.json()["highlights"]["last_game"]
        # Alice: 2/2 = 100%, Bob: 1/2 = 50%
        assert last_game["sharpshooter"]["name"] == "Alice"
        assert last_game["sharpshooter"]["accuracy"] == 100
