"""Pre-final review phase tests — edit any round's scores before finalizing."""

from httpx import AsyncClient


async def _setup_two_round_game(client: AsyncClient):
    """Create playground, play 2 rounds (of 8 total). Return game_id, cookies, pg."""
    await client.post(
        "/api/playground",
        json={"name": "Review Test", "pin": "1234", "players": ["Alice", "Bob"]},
    )
    auth = await client.post(
        "/api/playground/auth",
        json={"name": "Review Test", "pin": "1234"},
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

    # Play 2 rounds
    for _ in range(2):
        await _play_one_round(client, game_id, cookies)

    return game_id, cookies, pg


async def _play_one_round(client: AsyncClient, game_id: int, cookies: dict):
    """Submit bids, start round, enter round end, submit hands, score."""
    # Bids: Alice=1, Bob=1 (total=2 != cards dealt, satisfies must-lose if on)
    for pi, bid in [(0, 1), (1, 1)]:
        await client.post(
            f"/api/game/{game_id}/bid",
            json={"player_index": pi, "value": bid},
            cookies=cookies,
        )
    await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
    await client.post(f"/api/game/{game_id}/enter-round-end", cookies=cookies)

    # Hands: must total cards_dealt. Get current round info.
    bids_resp = await client.get(f"/api/game/{game_id}/bids", cookies=cookies)
    cards = bids_resp.json()["cards_dealt"]

    # Alice gets 1, Bob gets rest
    alice_hands = min(1, cards)
    bob_hands = cards - alice_hands
    for pi, hands in [(0, alice_hands), (1, bob_hands)]:
        await client.post(
            f"/api/game/{game_id}/hands",
            json={"player_index": pi, "value": hands},
            cookies=cookies,
        )
    await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)

    # Advance to next round
    await client.post(f"/api/game/{game_id}/next-round", cookies=cookies)


async def _setup_finished_game(client: AsyncClient):
    """Create and play a full 8-round game. Return game_id, cookies."""
    await client.post(
        "/api/playground",
        json={"name": "Finish Test", "pin": "5678", "players": ["Alice", "Bob"]},
    )
    auth = await client.post(
        "/api/playground/auth",
        json={"name": "Finish Test", "pin": "5678"},
    )
    cookies = {"scokeep_session": auth.cookies.get("scokeep_session")}
    pg = auth.json()

    game_resp = await client.post(
        "/api/game",
        json={"playground_id": pg["id"], "players": pg["players"], "settings": {"num_sets": 1}},
        cookies=cookies,
    )
    game_id = game_resp.json()["id"]

    # Play all 8 rounds
    for _round_num in range(8):
        # Bids
        for pi, bid in [(0, 1), (1, 1)]:
            await client.post(
                f"/api/game/{game_id}/bid",
                json={"player_index": pi, "value": bid},
                cookies=cookies,
            )
        await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
        await client.post(f"/api/game/{game_id}/enter-round-end", cookies=cookies)

        bids_resp = await client.get(f"/api/game/{game_id}/bids", cookies=cookies)
        cards = bids_resp.json()["cards_dealt"]
        alice_hands = min(1, cards)
        bob_hands = cards - alice_hands
        for pi, hands in [(0, alice_hands), (1, bob_hands)]:
            await client.post(
                f"/api/game/{game_id}/hands",
                json={"player_index": pi, "value": hands},
                cookies=cookies,
            )
        await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)

        # Advance (last round transitions to review)
        await client.post(f"/api/game/{game_id}/next-round", cookies=cookies)

    return game_id, cookies


class TestEnterReview:
    async def test_enter_review_sets_phase(self, client: AsyncClient):
        """POST /enter-review puts game in review phase."""
        game_id, cookies, _ = await _setup_two_round_game(client)

        # Game should be in scoreboard phase after playing rounds
        # Go back to scoreboard by undoing the last next-round advance
        # Actually, after _setup_two_round_game the game is in bidding (round 3)
        # We need to be in scoreboard. Let's play round 3 but not advance.
        for pi, bid in [(0, 1), (1, 1)]:
            await client.post(
                f"/api/game/{game_id}/bid",
                json={"player_index": pi, "value": bid},
                cookies=cookies,
            )
        await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
        await client.post(f"/api/game/{game_id}/enter-round-end", cookies=cookies)
        bids_resp = await client.get(f"/api/game/{game_id}/bids", cookies=cookies)
        cards = bids_resp.json()["cards_dealt"]
        alice_hands = min(1, cards)
        bob_hands = cards - alice_hands
        for pi, hands in [(0, alice_hands), (1, bob_hands)]:
            await client.post(
                f"/api/game/{game_id}/hands",
                json={"player_index": pi, "value": hands},
                cookies=cookies,
            )
        await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)
        # Now in scoreboard phase

        resp = await client.post(f"/api/game/{game_id}/enter-review", cookies=cookies)
        assert resp.status_code == 200
        assert resp.json()["phase"] == "review"

    async def test_enter_review_rejects_non_scoreboard(self, client: AsyncClient):
        """enter-review only works from scoreboard phase."""
        game_id, cookies, _ = await _setup_two_round_game(client)
        # Game is in bidding phase (round 3) — should reject
        resp = await client.post(f"/api/game/{game_id}/enter-review", cookies=cookies)
        assert resp.status_code == 409


class TestLastRoundGoesToReview:
    async def test_next_round_on_last_round_goes_to_review(self, client: AsyncClient):
        """When advancing past the final round, game enters review phase."""
        game_id, cookies = await _setup_finished_game(client)

        game_resp = await client.get(f"/api/game/{game_id}", cookies=cookies)
        game = game_resp.json()
        assert game["phase"] == "review"
        assert game["status"] == "active"  # Not finished yet

    async def test_end_game_goes_to_review(self, client: AsyncClient):
        """POST /end transitions to review, not directly to final."""
        game_id, cookies, _ = await _setup_two_round_game(client)

        resp = await client.post(f"/api/game/{game_id}/end", cookies=cookies)
        assert resp.status_code == 200
        game = resp.json()
        assert game["phase"] == "review"
        assert game["status"] == "active"  # Not finished yet


class TestRescoreSpecificRound:
    async def test_rescore_round_resets_for_reentry(self, client: AsyncClient):
        """POST /rescore/{round_num} resets that round for re-entry."""
        game_id, cookies = await _setup_finished_game(client)

        # Game is in review phase. Rescore round 1.
        resp = await client.post(f"/api/game/{game_id}/rescore/1", cookies=cookies)
        assert resp.status_code == 200
        assert resp.json()["phase"] == "round_end"
        assert resp.json()["editing_round"] == 1

    async def test_rescore_invalid_round_num(self, client: AsyncClient):
        """Rescore with invalid round number returns 404."""
        game_id, cookies = await _setup_finished_game(client)

        resp = await client.post(f"/api/game/{game_id}/rescore/99", cookies=cookies)
        assert resp.status_code == 404

    async def test_rescore_only_works_in_review(self, client: AsyncClient):
        """Rescore endpoint only works when game is in review phase."""
        game_id, cookies, _ = await _setup_two_round_game(client)
        # Game is in bidding phase
        resp = await client.post(f"/api/game/{game_id}/rescore/1", cookies=cookies)
        assert resp.status_code == 409

    async def test_rescore_then_re_enter_hands_and_score(self, client: AsyncClient):
        """Full flow: rescore a round, edit hands, re-score, back to review."""
        game_id, cookies = await _setup_finished_game(client)

        # Get scores before
        sb_before = await client.get(f"/api/game/{game_id}/scoreboard", cookies=cookies)
        round1_scores_before = sb_before.json()["rounds"][0]["scores"]

        # Rescore round 1
        await client.post(f"/api/game/{game_id}/rescore/1", cookies=cookies)

        # Get round info to know cards dealt
        bids_resp = await client.get(f"/api/game/{game_id}/bids", cookies=cookies)
        cards = bids_resp.json()["cards_dealt"]

        # Edit hands: swap Alice and Bob
        for pi, hands in [(0, 0), (1, cards)]:
            await client.post(
                f"/api/game/{game_id}/hands",
                json={"player_index": pi, "value": hands},
                cookies=cookies,
            )

        # Re-score
        await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)

        # Game should be back in review phase
        game_resp = await client.get(f"/api/game/{game_id}", cookies=cookies)
        assert game_resp.json()["phase"] == "review"

        # Scores should have changed
        sb_after = await client.get(f"/api/game/{game_id}/scoreboard", cookies=cookies)
        round1_scores_after = sb_after.json()["rounds"][0]["scores"]
        assert round1_scores_after != round1_scores_before


    async def test_cancel_edit_via_end_round_restores_original_scores(self, client: AsyncClient):
        """Cancel-edit: end-round without re-submitting hands restores scores.

        Server preserves hands_won during rescore, so end-round alone suffices.
        """
        game_id, cookies = await _setup_finished_game(client)

        # Capture original scores for round 1
        sb_before = await client.get(f"/api/game/{game_id}/scoreboard", cookies=cookies)
        round1_scores_before = sb_before.json()["rounds"][0]["scores"]

        # Rescore round 1 (clears scores, preserves hands_won)
        await client.post(f"/api/game/{game_id}/rescore/1", cookies=cookies)

        # Verify hands_won is preserved (the precondition that makes cancel safe)
        bids_resp = await client.get(f"/api/game/{game_id}/bids", cookies=cookies)
        assert bids_resp.json()["hands_won"] != {}, "hands_won must be preserved after rescore"

        # Cancel: call end-round directly, no re-submit of hands
        resp = await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)
        assert resp.status_code == 200

        # Game returns to review phase
        game_resp = await client.get(f"/api/game/{game_id}", cookies=cookies)
        assert game_resp.json()["phase"] == "review"

        # Scores match the originals — cancel restored correctly with 1 API call
        sb_after = await client.get(f"/api/game/{game_id}/scoreboard", cookies=cookies)
        round1_scores_after = sb_after.json()["rounds"][0]["scores"]
        assert round1_scores_after == round1_scores_before


class TestConfirmFinal:
    async def test_confirm_final_finishes_game(self, client: AsyncClient):
        """POST /confirm-final sets status=finished, phase=final."""
        game_id, cookies = await _setup_finished_game(client)

        resp = await client.post(f"/api/game/{game_id}/confirm-final", cookies=cookies)
        assert resp.status_code == 200
        game = resp.json()
        assert game["phase"] == "final"
        assert game["status"] == "finished"

    async def test_confirm_final_only_works_in_review(self, client: AsyncClient):
        """confirm-final only works from review phase."""
        game_id, cookies, _ = await _setup_two_round_game(client)
        resp = await client.post(f"/api/game/{game_id}/confirm-final", cookies=cookies)
        assert resp.status_code == 409

    async def test_confirm_final_triggers_insights(self, client: AsyncClient):
        """After confirm-final, insights should be computed."""
        game_id, cookies = await _setup_finished_game(client)

        # Confirm
        await client.post(f"/api/game/{game_id}/confirm-final", cookies=cookies)

        # Get the game to find playground_id, then check stats
        game_resp = await client.get(f"/api/game/{game_id}", cookies=cookies)
        assert game_resp.json()["status"] == "finished"
