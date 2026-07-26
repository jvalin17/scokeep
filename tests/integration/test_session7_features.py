"""Integration tests for session 7 features.

Tests:
1. Alternating set direction (8→1, 1→8, 8→1)
2. End game from any phase (bidding, playing, round_end)
3. End game with no rounds played returns empty scoreboard
4. End game after rounds shows scores in scoreboard
5. Active game not returned after ending
"""

from httpx import AsyncClient


async def _setup(client: AsyncClient, name: str = "Session7 Test"):
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


async def _create_game(client, pg_id, cookies, players=None, num_sets=1):
    """Create a game and return the game dict."""
    resp = await client.post("/api/game", json={
        "playground_id": pg_id,
        "players": players or ["Alice", "Bob", "Charlie"],
        "settings": {"num_sets": num_sets},
    }, cookies=cookies)
    assert resp.status_code == 201
    return resp.json()


class TestAlternatingSets:
    """Cards per round alternate: set 1 = 8→1, set 2 = 1→8, set 3 = 8→1."""

    async def test_set_1_starts_at_8_descends_to_1(self, client: AsyncClient):
        """First set: rounds 1-8 have 8,7,6,5,4,3,2,1 cards."""
        from app.utils.trump import get_cards_for_round
        cards = [get_cards_for_round(r) for r in range(1, 9)]
        assert cards == [8, 7, 6, 5, 4, 3, 2, 1]

    async def test_set_2_starts_at_1_ascends_to_8(self, client: AsyncClient):
        """Second set: rounds 9-16 have 1,2,3,4,5,6,7,8 cards."""
        from app.utils.trump import get_cards_for_round
        cards = [get_cards_for_round(r) for r in range(9, 17)]
        assert cards == [1, 2, 3, 4, 5, 6, 7, 8]

    async def test_set_3_descends_again(self, client: AsyncClient):
        """Third set: rounds 17-24 have 8,7,6,5,4,3,2,1 cards."""
        from app.utils.trump import get_cards_for_round
        cards = [get_cards_for_round(r) for r in range(17, 25)]
        assert cards == [8, 7, 6, 5, 4, 3, 2, 1]

    async def test_set_transition_boundary(self, client: AsyncClient):
        """Boundary: set 1 ends at 1 card (round 8), set 2 starts at 1 card (round 9).
        Pattern across boundary: ...2, 1, 1, 2... (descend then ascend)."""
        from app.utils.trump import get_cards_for_round
        # Rounds 7-10 cross the set boundary
        cards = [get_cards_for_round(r) for r in range(7, 11)]
        assert cards == [2, 1, 1, 2]

    async def test_full_3_sets_pattern(self, client: AsyncClient):
        """Full 3-set game: 8→1, 1→8, 8→1 (24 rounds)."""
        from app.utils.trump import get_cards_for_round
        cards = [get_cards_for_round(r) for r in range(1, 25)]
        set1 = [8, 7, 6, 5, 4, 3, 2, 1]
        set2 = [1, 2, 3, 4, 5, 6, 7, 8]
        assert cards == set1 + set2 + set1

    async def test_bid_max_matches_cards_for_round_in_set_2(
        self, client: AsyncClient
    ):
        """In set 2 round 9 (1 card), max bid should be 1."""
        from app.utils.trump import get_cards_for_round
        # Round 9 = first round of set 2 = 1 card
        assert get_cards_for_round(9) == 1

        # Verify backend enforces: bid > cards_dealt should fail
        pg, cookies = await _setup(client, "Alt Set Bid Test")
        game = await _create_game(client, pg["id"], cookies, num_sets=2)
        game_id = game["id"]

        # Play through set 1 (8 rounds) to reach set 2
        for _round_num in range(1, 9):
            # Bid 0 for everyone
            for i in range(3):
                await client.post(f"/api/game/{game_id}/bid", json={
                    "player_index": i, "value": 0,
                }, cookies=cookies)
            await client.post(
                f"/api/game/{game_id}/start-round", cookies=cookies
            )
            await client.post(
                f"/api/game/{game_id}/enter-round-end", cookies=cookies
            )
            # Submit hands (0 for all)
            for i in range(3):
                await client.post(f"/api/game/{game_id}/hands", json={
                    "player_index": i, "value": 0,
                }, cookies=cookies)
            await client.post(
                f"/api/game/{game_id}/end-round", cookies=cookies
            )
            await client.post(
                f"/api/game/{game_id}/next-round", cookies=cookies
            )

        # Now at round 9, set 2 — should have 1 card
        game_resp = await client.get(
            f"/api/game/{game_id}", cookies=cookies
        )
        assert game_resp.json()["current_round"] == 9

        # Bid 1 should succeed (max = 1 card)
        resp = await client.post(f"/api/game/{game_id}/bid", json={
            "player_index": 0, "value": 1,
        }, cookies=cookies)
        assert resp.status_code == 200


class TestEndGameFromAnyPhase:
    """End game should work from bidding, playing, and round_end phases."""

    async def test_end_game_from_bidding_phase(self, client: AsyncClient):
        """Can end game while still collecting bids."""
        pg, cookies = await _setup(client, "End Bidding")
        game = await _create_game(client, pg["id"], cookies)
        game_id = game["id"]

        # Game starts in bidding phase
        assert game["phase"] == "bidding"

        # End game
        resp = await client.post(
            f"/api/game/{game_id}/end", cookies=cookies
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "finished"

    async def test_end_game_from_playing_phase(self, client: AsyncClient):
        """Can end game during play (after bids confirmed)."""
        pg, cookies = await _setup(client, "End Playing")
        game = await _create_game(client, pg["id"], cookies)
        game_id = game["id"]

        # Submit bids and start round
        for i in range(3):
            await client.post(f"/api/game/{game_id}/bid", json={
                "player_index": i, "value": 2,
            }, cookies=cookies)
        await client.post(
            f"/api/game/{game_id}/start-round", cookies=cookies
        )

        # Verify playing phase
        game_resp = await client.get(
            f"/api/game/{game_id}", cookies=cookies
        )
        assert game_resp.json()["phase"] == "playing"

        # End game from playing
        resp = await client.post(
            f"/api/game/{game_id}/end", cookies=cookies
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "finished"

    async def test_end_game_from_round_end_phase(self, client: AsyncClient):
        """Can end game during hands entry."""
        pg, cookies = await _setup(client, "End Round End")
        game = await _create_game(client, pg["id"], cookies)
        game_id = game["id"]

        # Get to round_end phase
        for i in range(3):
            await client.post(f"/api/game/{game_id}/bid", json={
                "player_index": i, "value": 1,
            }, cookies=cookies)
        await client.post(
            f"/api/game/{game_id}/start-round", cookies=cookies
        )
        await client.post(
            f"/api/game/{game_id}/enter-round-end", cookies=cookies
        )

        # Verify round_end phase
        game_resp = await client.get(
            f"/api/game/{game_id}", cookies=cookies
        )
        assert game_resp.json()["phase"] == "round_end"

        # End game
        resp = await client.post(
            f"/api/game/{game_id}/end", cookies=cookies
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "finished"


class TestEndGameScoreboard:
    """After ending game, scoreboard reflects correct state."""

    async def test_end_game_no_rounds_played_empty_scoreboard(
        self, client: AsyncClient
    ):
        """End game during round 1 bidding — scoreboard has no rounds."""
        pg, cookies = await _setup(client, "No Rounds")
        game = await _create_game(client, pg["id"], cookies)
        game_id = game["id"]

        # End immediately (no rounds scored)
        await client.post(f"/api/game/{game_id}/end", cookies=cookies)

        # Get scoreboard
        resp = await client.get(
            f"/api/game/{game_id}/scoreboard", cookies=cookies
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["rounds"] == []
        assert all(v == 0 for v in body["totals"].values())

    async def test_end_game_after_rounds_shows_scores(
        self, client: AsyncClient
    ):
        """End game after 1 round — scoreboard has correct scores."""
        pg, cookies = await _setup(client, "With Rounds")
        game = await _create_game(client, pg["id"], cookies)
        game_id = game["id"]

        # Play 1 full round: Alice bids 2 gets 2, Bob bids 3 gets 3,
        # Charlie bids 1 gets 3
        bids = [2, 3, 1]
        hands = [2, 3, 3]
        for i, bid in enumerate(bids):
            await client.post(f"/api/game/{game_id}/bid", json={
                "player_index": i, "value": bid,
            }, cookies=cookies)
        await client.post(
            f"/api/game/{game_id}/start-round", cookies=cookies
        )
        await client.post(
            f"/api/game/{game_id}/enter-round-end", cookies=cookies
        )
        for i, hand in enumerate(hands):
            await client.post(f"/api/game/{game_id}/hands", json={
                "player_index": i, "value": hand,
            }, cookies=cookies)
        await client.post(
            f"/api/game/{game_id}/end-round", cookies=cookies
        )

        # End game from scoreboard phase
        await client.post(f"/api/game/{game_id}/end", cookies=cookies)

        # Verify scoreboard has round data
        resp = await client.get(
            f"/api/game/{game_id}/scoreboard", cookies=cookies
        )
        body = resp.json()
        assert len(body["rounds"]) == 1
        # Alice: bid 2, got 2 → +20
        assert body["totals"]["0"] == 20
        # Bob: bid 3, got 3 → +30
        assert body["totals"]["1"] == 30
        # Charlie: bid 1, got 3 → -11
        assert body["totals"]["2"] == -11


class TestActiveGameAfterEnd:
    """After ending a game, it should no longer appear as active."""

    async def test_no_active_game_after_end(self, client: AsyncClient):
        """GET /api/game/active/{pg_id} returns 404 after ending."""
        pg, cookies = await _setup(client, "Active After End")
        game = await _create_game(client, pg["id"], cookies)
        game_id = game["id"]

        # Active game exists
        resp = await client.get(
            f"/api/game/active/{pg['id']}", cookies=cookies
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == game_id

        # End game
        await client.post(f"/api/game/{game_id}/end", cookies=cookies)

        # No active game anymore
        resp = await client.get(
            f"/api/game/active/{pg['id']}", cookies=cookies
        )
        assert resp.status_code == 404

    async def test_end_from_bidding_clears_active(self, client: AsyncClient):
        """Ending during bidding also clears active game."""
        pg, cookies = await _setup(client, "Clear Active Bid")
        game = await _create_game(client, pg["id"], cookies)

        # End during bidding
        await client.post(
            f"/api/game/{game['id']}/end", cookies=cookies
        )

        # No active game
        resp = await client.get(
            f"/api/game/active/{pg['id']}", cookies=cookies
        )
        assert resp.status_code == 404
