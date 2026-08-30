"""Re-score round tests — edit hands after scoring without losing bids."""

from httpx import AsyncClient


async def _setup_scored_round(client: AsyncClient):
    """Create playground, start game, bid, enter hands, score round. Return game_id + cookies."""
    await client.post(
        "/api/playground",
        json={"name": "Rescore Test", "pin": "1234", "players": ["Alice", "Bob", "Charlie"]},
    )
    auth = await client.post(
        "/api/playground/auth",
        json={"name": "Rescore Test", "pin": "1234"},
    )
    cookies = {"scokeep_session": auth.cookies.get("scokeep_session")}
    pg = auth.json()

    game_resp = await client.post(
        "/api/game",
        json={"playground_id": pg["id"], "players": pg["players"], "settings": {"num_sets": 1}},
        cookies=cookies,
    )
    game = game_resp.json()
    game_id = game["id"]

    # Submit bids: Alice=2, Bob=3, Charlie=1
    for pi, bid in [(0, 2), (1, 3), (2, 1)]:
        await client.post(
            f"/api/game/{game_id}/bid", json={"player_index": pi, "value": bid}, cookies=cookies
        )

    # Start round
    await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)

    # Enter round end
    await client.post(f"/api/game/{game_id}/enter-round-end", cookies=cookies)

    # Submit hands: Alice=2, Bob=3, Charlie=3 (Charlie wrong — should be 3 but bid was 1)
    for pi, hands in [(0, 2), (1, 3), (2, 3)]:
        await client.post(
            f"/api/game/{game_id}/hands", json={"player_index": pi, "value": hands}, cookies=cookies
        )

    # Score round
    await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)

    return game_id, cookies


class TestEnterRescore:
    async def test_enter_rescore_resets_phase(self, client: AsyncClient):
        """POST /enter-rescore puts game back in round_end phase."""
        game_id, cookies = await _setup_scored_round(client)

        resp = await client.post(f"/api/game/{game_id}/enter-rescore", cookies=cookies)
        assert resp.status_code == 200
        assert resp.json()["phase"] == "round_end"

    async def test_can_edit_individual_hands_after_rescore(self, client: AsyncClient):
        """After enter-rescore, individual hands can be edited."""
        game_id, cookies = await _setup_scored_round(client)

        # Original hands: Alice=2, Bob=3, Charlie=3 (total=8)
        await client.post(f"/api/game/{game_id}/enter-rescore", cookies=cookies)

        # Fix Charlie from 3 to 2, then fix Alice from 2 to 3
        # Must change Charlie first to free up a card for Alice
        resp = await client.post(
            f"/api/game/{game_id}/hands",
            json={"player_index": 2, "value": 2},
            cookies=cookies,
        )
        assert resp.status_code == 200

        resp = await client.post(
            f"/api/game/{game_id}/hands",
            json={"player_index": 0, "value": 3},
            cookies=cookies,
        )
        assert resp.status_code == 200

    async def test_rescore_preserves_bids(self, client: AsyncClient):
        """Bids must not change during re-score."""
        game_id, cookies = await _setup_scored_round(client)

        # Get bids before rescore
        bids_before = await client.get(f"/api/game/{game_id}/bids", cookies=cookies)
        original_bids = bids_before.json()["bids"]

        await client.post(f"/api/game/{game_id}/enter-rescore", cookies=cookies)

        # Edit hands: change Charlie from 3→2 first (free card), then Alice 2→3
        for pi, hands in [(2, 2), (0, 3)]:
            await client.post(
                f"/api/game/{game_id}/hands",
                json={"player_index": pi, "value": hands},
                cookies=cookies,
            )
        await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)

        # Bids must be unchanged
        bids_after = await client.get(f"/api/game/{game_id}/bids", cookies=cookies)
        assert bids_after.json()["bids"] == original_bids

    async def test_rescore_updates_scores(self, client: AsyncClient):
        """After re-scoring with different hands, scores must change."""
        game_id, cookies = await _setup_scored_round(client)

        # Get scores before
        sb_before = await client.get(f"/api/game/{game_id}/scoreboard", cookies=cookies)
        scores_before = sb_before.json()["rounds"][0]["scores"]

        await client.post(f"/api/game/{game_id}/enter-rescore", cookies=cookies)

        # Edit hands: change Charlie from 3→2 first (free card), then Alice 2→3
        for pi, hands in [(2, 2), (0, 3)]:
            await client.post(
                f"/api/game/{game_id}/hands",
                json={"player_index": pi, "value": hands},
                cookies=cookies,
            )
        await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)

        # Scores must be different
        sb_after = await client.get(f"/api/game/{game_id}/scoreboard", cookies=cookies)
        scores_after = sb_after.json()["rounds"][0]["scores"]
        assert scores_after != scores_before

    async def test_rescore_only_works_on_scoreboard_phase(self, client: AsyncClient):
        """enter-rescore should only work when game is in scoreboard phase."""
        game_id, cookies = await _setup_scored_round(client)

        # Already in scoreboard phase — should work
        resp = await client.post(f"/api/game/{game_id}/enter-rescore", cookies=cookies)
        assert resp.status_code == 200

        # Now in round_end phase — should fail
        resp2 = await client.post(f"/api/game/{game_id}/enter-rescore", cookies=cookies)
        assert resp2.status_code == 409

    async def test_enter_rescore_preserves_hands(self, client: AsyncClient):
        """enter-rescore must keep hands_won so the confirm screen can pre-fill."""
        game_id, cookies = await _setup_scored_round(client)

        # Original hands: Alice=2, Bob=3, Charlie=3
        await client.post(f"/api/game/{game_id}/enter-rescore", cookies=cookies)

        # Fetch the round — hands_won should still have the original values
        resp = await client.get(f"/api/game/{game_id}/bids", cookies=cookies)
        assert resp.status_code == 200
        hands = resp.json()["hands_won"]
        assert hands == {"0": 2, "1": 3, "2": 3}, f"Hands should be preserved, got: {hands}"

        # Scores should be cleared
        scores = resp.json()["scores"]
        assert scores == {}, f"Scores should be cleared, got: {scores}"

    async def test_rescore_blocked_on_finished_game(self, client: AsyncClient):
        """Cannot rescore after game is ended/finished."""
        game_id, cookies = await _setup_scored_round(client)

        # End the game
        await client.post(f"/api/game/{game_id}/end", cookies=cookies)

        # Rescore should fail — game phase is 'final', not 'scoreboard'
        resp = await client.post(f"/api/game/{game_id}/enter-rescore", cookies=cookies)
        assert resp.status_code == 409
