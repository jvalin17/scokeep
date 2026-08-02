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


class TestSetBoundaryDetection:
    """Verify game state at scoreboard enables set-boundary detection."""

    async def test_at_set_boundary_current_round_is_divisible(
        self, client: AsyncClient,
    ):
        """After completing round 4 of a 4-round set, current_round=4
        and current_round % rounds_per_set == 0 (set boundary)."""
        pg, cookies = await _setup(client, "SetBound Test")
        game_resp = await client.post("/api/game", json={
            "playground_id": pg["id"],
            "players": ["Lena", "Marco"],
            "settings": {"num_sets": 2, "rounds_per_set": 4},
        }, cookies=cookies)
        game_id = game_resp.json()["id"]

        # Play 4 rounds to complete set 1
        for round_num in range(4):
            cards = 4 - round_num
            for i in range(2):
                await client.post(f"/api/game/{game_id}/bid", json={
                    "player_index": i, "value": 0,
                }, cookies=cookies)
            await client.post(
                f"/api/game/{game_id}/start-round", cookies=cookies,
            )
            await client.post(
                f"/api/game/{game_id}/enter-round-end", cookies=cookies,
            )
            for i, hand in enumerate([0, cards]):
                await client.post(f"/api/game/{game_id}/hands", json={
                    "player_index": i, "value": hand,
                }, cookies=cookies)
            await client.post(
                f"/api/game/{game_id}/end-round", cookies=cookies,
            )
            if round_num < 3:
                await client.post(
                    f"/api/game/{game_id}/next-round", cookies=cookies,
                )

        # At scoreboard after round 4: game should be in scoreboard phase
        game_state = await client.get(
            f"/api/game/{game_id}", cookies=cookies,
        )
        game = game_state.json()
        assert game["phase"] == "scoreboard"
        assert game["status"] == "active"
        # current_round should be 4 (not yet advanced)
        assert game["current_round"] == 4
        # Set boundary: 4 % 4 == 0
        rounds_per_set = game["settings"]["rounds_per_set"]
        assert game["current_round"] % rounds_per_set == 0

    async def test_at_last_round_current_round_equals_total(
        self, client: AsyncClient,
    ):
        """After completing the final round, current_round == total_rounds
        and game is still active (not finished until next-round is called)."""
        pg, cookies = await _setup(client, "LastRound Test")
        game_resp = await client.post("/api/game", json={
            "playground_id": pg["id"],
            "players": ["Anya", "Riku"],
            "settings": {"num_sets": 1, "rounds_per_set": 4},
        }, cookies=cookies)
        game_id = game_resp.json()["id"]

        # Play all 4 rounds
        for round_num in range(4):
            cards = 4 - round_num
            for i in range(2):
                await client.post(f"/api/game/{game_id}/bid", json={
                    "player_index": i, "value": 0,
                }, cookies=cookies)
            await client.post(
                f"/api/game/{game_id}/start-round", cookies=cookies,
            )
            await client.post(
                f"/api/game/{game_id}/enter-round-end", cookies=cookies,
            )
            for i, hand in enumerate([0, cards]):
                await client.post(f"/api/game/{game_id}/hands", json={
                    "player_index": i, "value": hand,
                }, cookies=cookies)
            await client.post(
                f"/api/game/{game_id}/end-round", cookies=cookies,
            )
            if round_num < 3:
                await client.post(
                    f"/api/game/{game_id}/next-round", cookies=cookies,
                )

        # At scoreboard after final round
        game_state = await client.get(
            f"/api/game/{game_id}", cookies=cookies,
        )
        game = game_state.json()
        assert game["phase"] == "scoreboard"
        # Game must still be active so user can choose extend vs end
        assert game["status"] == "active"
        assert game["current_round"] == 4
        assert game["current_round"] >= game["total_rounds"]


class TestExtendAndPlayNextSet:
    """Extend game then play into the new set — full integration."""

    async def test_extend_then_next_round_plays_alternating_set(
        self, client: AsyncClient,
    ):
        """After extending a 1-set game, next set alternates direction (1→8)."""
        pg, cookies = await _setup(client, "Extend Play Alt")
        game_resp = await client.post("/api/game", json={
            "playground_id": pg["id"],
            "players": ["Nadia", "Carlos"],
            "settings": {"num_sets": 1, "rounds_per_set": 4},
        }, cookies=cookies)
        game = game_resp.json()
        game_id = game["id"]
        assert game["total_rounds"] == 4

        # Play all 4 rounds (set 1: 4,3,2,1 cards)
        for round_num in range(4):
            bids = [1, 1]
            cards = 4 - round_num  # descending
            hands = [1, cards - 1]
            for i, bid in enumerate(bids):
                await client.post(f"/api/game/{game_id}/bid", json={
                    "player_index": i, "value": bid,
                }, cookies=cookies)
            await client.post(
                f"/api/game/{game_id}/start-round", cookies=cookies,
            )
            await client.post(
                f"/api/game/{game_id}/enter-round-end", cookies=cookies,
            )
            for i, hand in enumerate(hands):
                await client.post(f"/api/game/{game_id}/hands", json={
                    "player_index": i, "value": hand,
                }, cookies=cookies)
            await client.post(
                f"/api/game/{game_id}/end-round", cookies=cookies,
            )
            if round_num < 3:
                await client.post(
                    f"/api/game/{game_id}/next-round", cookies=cookies,
                )

        # At scoreboard after round 4 — extend
        resp = await client.post(
            f"/api/game/{game_id}/extend", cookies=cookies,
        )
        assert resp.status_code == 200
        assert resp.json()["total_rounds"] == 8

        # Advance to round 5
        resp = await client.post(
            f"/api/game/{game_id}/next-round", cookies=cookies,
        )
        assert resp.status_code == 200
        assert resp.json()["current_round"] == 5

        # Round 5 is set 2, ascending: 1 card
        bids_resp = await client.post(f"/api/game/{game_id}/bid", json={
            "player_index": 0, "value": 0,
        }, cookies=cookies)
        assert bids_resp.json()["cards_dealt"] == 1

    async def test_extend_preserves_scores(self, client: AsyncClient):
        """Scores from before extend are preserved in scoreboard."""
        pg, cookies = await _setup(client, "Extend Scores")
        game_resp = await client.post("/api/game", json={
            "playground_id": pg["id"],
            "players": ["Lena", "Marco"],
            "settings": {"num_sets": 1, "rounds_per_set": 4},
        }, cookies=cookies)
        game_id = game_resp.json()["id"]

        # Round 1: 4 cards. Lena bids 3 makes 3 (+30), Marco bids 1 makes 1 (+11)
        for i, bid in enumerate([3, 1]):
            await client.post(f"/api/game/{game_id}/bid", json={
                "player_index": i, "value": bid,
            }, cookies=cookies)
        await client.post(
            f"/api/game/{game_id}/start-round", cookies=cookies,
        )
        await client.post(
            f"/api/game/{game_id}/enter-round-end", cookies=cookies,
        )
        for i, hand in enumerate([3, 1]):
            await client.post(f"/api/game/{game_id}/hands", json={
                "player_index": i, "value": hand,
            }, cookies=cookies)
        await client.post(
            f"/api/game/{game_id}/end-round", cookies=cookies,
        )

        sb = await client.get(
            f"/api/game/{game_id}/scoreboard", cookies=cookies,
        )
        assert sb.json()["totals"]["0"] == 30
        assert sb.json()["totals"]["1"] == 11

        # Extend
        await client.post(
            f"/api/game/{game_id}/extend", cookies=cookies,
        )

        # Totals unchanged
        sb_after = await client.get(
            f"/api/game/{game_id}/scoreboard", cookies=cookies,
        )
        assert sb_after.json()["totals"] == sb.json()["totals"]


class TestScoringFormula:
    """Integration: games with different scoring formulas."""

    async def test_zeros_formula_scores_10_for_bid_1(
        self, client: AsyncClient,
    ):
        """With zeros formula, bid 1 made = 10 (not 11)."""
        pg, cookies = await _setup(client, "Zeros Formula")
        game_resp = await client.post("/api/game", json={
            "playground_id": pg["id"],
            "players": ["Anya", "Riku"],
            "settings": {"scoring_formula": "kachuful_zeros"},
        }, cookies=cookies)
        game_id = game_resp.json()["id"]

        for i, bid in enumerate([1, 0]):
            await client.post(f"/api/game/{game_id}/bid", json={
                "player_index": i, "value": bid,
            }, cookies=cookies)
        await client.post(
            f"/api/game/{game_id}/start-round", cookies=cookies,
        )
        await client.post(
            f"/api/game/{game_id}/enter-round-end", cookies=cookies,
        )
        for i, hand in enumerate([1, 7]):
            await client.post(f"/api/game/{game_id}/hands", json={
                "player_index": i, "value": hand,
            }, cookies=cookies)
        await client.post(
            f"/api/game/{game_id}/end-round", cookies=cookies,
        )

        sb = await client.get(
            f"/api/game/{game_id}/scoreboard", cookies=cookies,
        )
        totals = sb.json()["totals"]
        assert totals["0"] == 10   # bid 1 made = 10 (zeros mode)
        assert totals["1"] == -10  # bid 0 missed

    async def test_standard_formula_scores_11_for_bid_1(
        self, client: AsyncClient,
    ):
        """With standard formula, bid 1 made = 11 (sanity check)."""
        pg, cookies = await _setup(client, "Standard Formula")
        game_resp = await client.post("/api/game", json={
            "playground_id": pg["id"],
            "players": ["Wei", "Priya"],
            "settings": {"scoring_formula": "kachuful_standard"},
        }, cookies=cookies)
        game_id = game_resp.json()["id"]

        for i, bid in enumerate([1, 0]):
            await client.post(f"/api/game/{game_id}/bid", json={
                "player_index": i, "value": bid,
            }, cookies=cookies)
        await client.post(
            f"/api/game/{game_id}/start-round", cookies=cookies,
        )
        await client.post(
            f"/api/game/{game_id}/enter-round-end", cookies=cookies,
        )
        for i, hand in enumerate([1, 7]):
            await client.post(f"/api/game/{game_id}/hands", json={
                "player_index": i, "value": hand,
            }, cookies=cookies)
        await client.post(
            f"/api/game/{game_id}/end-round", cookies=cookies,
        )

        sb = await client.get(
            f"/api/game/{game_id}/scoreboard", cookies=cookies,
        )
        totals = sb.json()["totals"]
        assert totals["0"] == 11   # bid 1 made = 11 (standard)
        assert totals["1"] == -10  # bid 0 missed
