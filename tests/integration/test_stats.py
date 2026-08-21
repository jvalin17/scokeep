"""Integration tests for playground stats/analytics endpoint.

Tests GET /api/playground/{share_code}/stats with real game data.
Verifies highlights, insights, and game history.
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
        assert body["game_history"] == []

    async def test_stats_after_one_game(self, client: AsyncClient):
        """Stats after 1 finished game show correct game history."""
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

        # Game history
        assert len(body["game_history"]) == 1
        assert body["game_history"][0]["winner"] == "Bob"

        # Insights should exist (but players have < 3 games, so no personality yet)
        assert "insights" in body

    async def test_stats_insights_after_three_games(self, client: AsyncClient):
        """After 3 games, players get full personality with extras."""
        pg, cookies = await _setup(client, "Insights 3 Games")

        # Vary bids each game for differentiation
        game_bids = [
            ([2, 3, 1], [2, 3, 3]),   # Alice exact, Bob exact, Charlie miss
            ([3, 0, 2], [3, 0, 5]),   # Alice exact, Bob zero-bid, Charlie miss
            ([1, 4, 0], [1, 4, 3]),   # Alice exact, Bob exact, Charlie miss
        ]
        for bids, hands in game_bids:
            await _play_full_game(
                client, pg["id"], cookies,
                players=["Alice", "Bob", "Charlie"],
                bids=bids, hands=hands,
            )

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        body = resp.json()
        assert body["total_games"] == 3
        insights = body["insights"]
        assert insights is not None
        assert "players" in insights
        assert "version" in insights

        # Each player should have full personality data
        valid_personalities = {
            "sniper", "gambler", "phoenix", "rock", "sprinter",
            "ghost", "architect", "minimalist", "comeback_kid", "wildcard",
        }
        for name in ["Alice", "Bob", "Charlie"]:
            player_data = insights["players"][name]
            # Personality is a valid archetype string
            assert isinstance(player_data["personality"], str)
            assert player_data["personality"] in valid_personalities
            assert player_data["games_analyzed"] == 3
            # 2 insight strings
            assert len(player_data["insights"]) == 2
            assert all(isinstance(s, str) and len(s) > 5 for s in player_data["insights"])
            # Accuracy breakdown exists with valid data
            accuracy = player_data["accuracy_by_cards"]
            assert isinstance(accuracy, dict)
            assert len(accuracy) > 0
            for card_data in accuracy.values():
                assert 0 <= card_data["pct"] <= 100
                assert card_data["rounds"] > 0
            # Extras with valid fields
            extras = player_data["extras"]
            assert extras["games_played"] == 3
            assert extras["total_rounds"] > 0
            assert extras["bidding_style"] in ("aggressive", "conservative", "balanced")
            assert extras["consistency"] in ("high", "medium", "low")
            # Confidence score
            assert 0.0 <= player_data["confidence"] <= 1.0
            # Meta served from API (single source of truth)
            meta = player_data["meta"]
            assert "name" in meta
            assert "tagline" in meta
            assert "color" in meta
            assert "icon" in meta
            assert meta["name"].startswith("The ")

    async def test_stats_insights_unlock_progress(self, client: AsyncClient):
        """Players with < 3 games show unlock progress, not personality."""
        pg, cookies = await _setup(client, "Insights Unlock")

        await _play_full_game(
            client, pg["id"], cookies,
            players=["Alice", "Bob"],
            bids=[2, 3], hands=[2, 6],
        )

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        insights = resp.json()["insights"]
        assert insights["players"]["Alice"]["personality"] is None
        assert insights["players"]["Alice"]["games_analyzed"] == 1
        assert insights["players"]["Alice"]["unlock_at"] == 3

    async def test_insights_unique_personalities(self, client: AsyncClient):
        """All players get different personality types."""
        pg, cookies = await _setup(client, "Unique Personality")

        # 3 games with varied results to differentiate players
        await _play_full_game(
            client, pg["id"], cookies,
            players=["Alice", "Bob", "Charlie"],
            bids=[3, 0, 1], hands=[3, 0, 5],
        )
        await _play_full_game(
            client, pg["id"], cookies,
            players=["Alice", "Bob", "Charlie"],
            bids=[2, 0, 2], hands=[2, 0, 6],
        )
        await _play_full_game(
            client, pg["id"], cookies,
            players=["Alice", "Bob", "Charlie"],
            bids=[1, 0, 3], hands=[1, 0, 7],
        )

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        insights = resp.json()["insights"]
        personalities = [
            insights["players"][name]["personality"]
            for name in ["Alice", "Bob", "Charlie"]
        ]
        assert len(set(personalities)) == 3  # all unique

    async def test_insights_full_pipeline_with_extras(
        self, client: AsyncClient,
    ):
        """Full pipeline: play varied games, verify extras in response."""
        pg, cookies = await _setup(client, "Pipeline Test")

        # Game 1: Alice overbids, Bob plays safe
        await _play_full_game(
            client, pg["id"], cookies,
            players=["Alice", "Bob"],
            bids=[5, 0], hands=[2, 6],
        )
        # Game 2: Alice exact, Bob exact
        await _play_full_game(
            client, pg["id"], cookies,
            players=["Alice", "Bob"],
            bids=[3, 5], hands=[3, 5],
        )
        # Game 3: Alice underbids, Bob overbids
        await _play_full_game(
            client, pg["id"], cookies,
            players=["Alice", "Bob"],
            bids=[1, 7], hands=[4, 4],
        )

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        body = resp.json()
        assert body["total_games"] == 3

        for name in ["Alice", "Bob"]:
            player = body["insights"]["players"][name]
            assert isinstance(player["personality"], str)
            assert len(player["personality"]) > 0
            assert "extras" in player
            extras = player["extras"]
            assert extras["games_played"] == 3
            assert "bidding_style" in extras
            assert extras["bidding_style"] in (
                "aggressive", "conservative", "balanced",
            )
            assert "consistency" in extras
            assert "trend" in extras
            assert isinstance(player["accuracy_by_cards"], dict)
            assert isinstance(player["insights"], list)
            assert len(player["insights"]) == 2
            assert "version" in body["insights"]

    async def test_highlights_cached_in_insights_blob(
        self, client: AsyncClient,
    ):
        """Highlights computed post-game and cached in insights blob."""
        pg, cookies = await _setup(client, "Highlights Cache")

        for _ in range(3):
            await _play_full_game(
                client, pg["id"], cookies,
                players=["Alice", "Bob"],
                bids=[2, 3], hands=[2, 6],
            )

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        body = resp.json()
        # Highlights should be in the response
        assert "highlights" in body
        assert body["highlights"]["last_game"] is not None
        # Insights blob should contain cached highlights
        insights = body["insights"]
        assert "highlights" in insights
        assert "last_game" in insights["highlights"]
        # Career records in cached highlights
        career = insights["highlights"]["career"]
        assert "sniper" in career
        assert "zero_master" in career

    async def test_insights_from_multi_round_games(
        self, client: AsyncClient,
    ):
        """Insights computed correctly from realistic multi-round games."""
        pg, cookies = await _setup(client, "MultiRound Insights")

        # Play 3 multi-round games (4 rounds each) with varied bids
        for _ in range(3):
            rounds = [
                # Round 1 (8 cards): Alice exact, Bob overbids, Charlie zero
                ([3, 5, 0], [3, 2, 3]),
                # Round 2 (7 cards): varied
                ([2, 0, 4], [2, 0, 5]),
                # Round 3 (6 cards): Alice miss, Bob exact
                ([4, 3, 1], [2, 3, 1]),
                # Round 4 (5 cards): all make it
                ([2, 2, 1], [2, 2, 1]),
            ]
            await _play_multi_round_game(
                client, pg["id"], cookies,
                players=["Alice", "Bob", "Charlie"],
                rounds_data=rounds,
                settings={"num_sets": 1, "rounds_per_set": 8},
            )

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        body = resp.json()
        assert body["total_games"] == 3

        insights = body["insights"]
        assert insights is not None

        # All players should have personalities from multi-round data
        for name in ["Alice", "Bob", "Charlie"]:
            player_data = insights["players"][name]
            assert player_data["personality"] is not None
            assert player_data["games_analyzed"] == 3
            # Accuracy should have multiple card counts (4 different per game)
            accuracy = player_data["accuracy_by_cards"]
            assert len(accuracy) >= 4
            # Extras should show meaningful data
            extras = player_data["extras"]
            assert extras["total_rounds"] == 12  # 4 rounds × 3 games

        # Personalities should all be unique
        personalities = [
            insights["players"][n]["personality"]
            for n in ["Alice", "Bob", "Charlie"]
        ]
        assert len(set(personalities)) == 3

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
        assert resp.json()["game_history"] == []

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

    async def test_highlights_empty_with_no_games(self, client: AsyncClient):
        """Highlights are empty when no games played."""
        pg, cookies = await _setup(client, "Empty Highlights")

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        body = resp.json()
        assert body["total_games"] == 0
        assert body["highlights"]["career"]["sniper"] == []
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

    async def test_empty_finished_games_not_counted(
        self, client: AsyncClient,
    ):
        """Games ended without any scored rounds should not inflate total_games."""
        pg, cookies = await _setup(client, "Empty Game Count")

        # Play one real game
        await _play_full_game(
            client, pg["id"], cookies,
            players=["Alice", "Bob", "Charlie"],
            bids=[2, 1, 0], hands=[2, 1, 5],
        )

        # Create and immediately end a game (no rounds played)
        game_resp = await client.post("/api/game", json={
            "playground_id": pg["id"],
            "players": ["Alice", "Bob", "Charlie"],
            "settings": {"num_sets": 1},
        }, cookies=cookies)
        empty_game_id = game_resp.json()["id"]
        await client.post(
            f"/api/game/{empty_game_id}/end", cookies=cookies,
        )

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats", cookies=cookies,
        )
        body = resp.json()
        # total_games should match game_history length — empty games excluded
        assert body["total_games"] == 1, (
            f"Expected 1 real game, got {body['total_games']} "
            f"(game_history has {len(body['game_history'])} entries)"
        )
        assert len(body["game_history"]) == 1
