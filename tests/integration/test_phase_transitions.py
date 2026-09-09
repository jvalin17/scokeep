"""Phase transition tests — verify every state change and catch stuck states.

Tests the full state machine:
  bidding → playing → round_end → scoreboard → bidding (next round)
  scoreboard → final (end game)

For each phase, tests:
  1. Valid transitions work
  2. Invalid transitions return 409 (not 500, not stuck)
  3. State is consistent after every transition
  4. Undo works correctly from every reachable state
"""

from httpx import AsyncClient


async def _setup(client: AsyncClient):
    """Create playground, auth, return (playground_id, cookies)."""
    r = await client.post(
        "/api/playground",
        json={
            "name": "Phase Test",
            "pin": "1234",
            "players": ["Alice", "Bob", "Charlie"],
        },
    )
    pg = r.json()
    r = await client.post(
        "/api/playground/auth",
        json={
            "name": "Phase Test",
            "pin": "1234",
        },
    )
    cookies = {"scokeep_session": r.cookies.get("scokeep_session")}
    return pg["id"], cookies


async def _create_game(client, pg_id, cookies, **settings):
    """Create a kachuful game, return game_id."""
    r = await client.post(
        "/api/game",
        json={
            "playground_id": pg_id,
            "players": ["Alice", "Bob", "Charlie"],
            "settings": {"num_sets": 1, **settings},
        },
        cookies=cookies,
    )
    assert r.status_code == 201
    return r.json()["id"]


async def _assert_phase(client, game_id, cookies, expected_phase):
    """Assert the game is in the expected phase."""
    r = await client.get(f"/api/game/{game_id}", cookies=cookies)
    assert r.status_code == 200
    actual = r.json()["phase"]
    assert actual == expected_phase, f"Expected phase '{expected_phase}', got '{actual}'"
    return r.json()


async def _submit_all_bids(client, game_id, cookies, bids=None):
    """Submit bids for all 3 players."""
    bids = bids or [1, 0, 2]
    for i, v in enumerate(bids):
        r = await client.post(
            f"/api/game/{game_id}/bid",
            json={"player_index": i, "value": v},
            cookies=cookies,
        )
        assert r.status_code == 200, f"Bid {i} failed: {r.text}"


async def _submit_all_hands(client, game_id, cookies, hands=None):
    """Submit hands for all 3 players."""
    hands = hands or [1, 0, 2]
    for i, v in enumerate(hands):
        r = await client.post(
            f"/api/game/{game_id}/hands",
            json={"player_index": i, "value": v},
            cookies=cookies,
        )
        assert r.status_code == 200, f"Hands {i} failed: {r.text}"


async def _play_full_round(client, game_id, cookies, bids=None, hands=None):
    """Play a complete round: bid → start → enter-end → hands → end-round."""
    bids = bids or [1, 0, 2]
    hands = hands or bids  # default: everyone makes their bid
    await _submit_all_bids(client, game_id, cookies, bids)
    await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
    await client.post(f"/api/game/{game_id}/enter-round-end", cookies=cookies)
    await _submit_all_hands(client, game_id, cookies, hands)
    r = await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)
    assert r.status_code == 200
    return r.json()


class TestBiddingPhase:
    """Tests for the bidding phase."""

    async def test_game_starts_in_bidding(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        await _assert_phase(client, game_id, cookies, "bidding")

    async def test_submit_bid_works_in_bidding(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        r = await client.post(
            f"/api/game/{game_id}/bid", json={"player_index": 0, "value": 2}, cookies=cookies
        )
        assert r.status_code == 200

    async def test_start_round_requires_all_bids(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        # Only 1 bid
        await client.post(
            f"/api/game/{game_id}/bid", json={"player_index": 0, "value": 1}, cookies=cookies
        )
        r = await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
        assert r.status_code == 400
        # Game still in bidding
        await _assert_phase(client, game_id, cookies, "bidding")

    async def test_hands_rejected_in_bidding(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        r = await client.post(
            f"/api/game/{game_id}/hands", json={"player_index": 0, "value": 1}, cookies=cookies
        )
        assert r.status_code == 409

    async def test_enter_round_end_rejected_in_bidding(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        r = await client.post(f"/api/game/{game_id}/enter-round-end", cookies=cookies)
        assert r.status_code == 409

    async def test_end_round_rejected_in_bidding(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        r = await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)
        assert r.status_code == 400

    async def test_next_round_rejected_in_bidding(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        r = await client.post(f"/api/game/{game_id}/next-round", cookies=cookies)
        assert r.status_code == 409


class TestBiddingToPlaying:
    """Transition: bidding → playing via start-round."""

    async def test_start_round_transitions_to_playing(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        await _submit_all_bids(client, game_id, cookies)
        r = await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
        assert r.status_code == 200
        await _assert_phase(client, game_id, cookies, "playing")

    async def test_double_start_round_rejected(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        await _submit_all_bids(client, game_id, cookies)
        await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
        r = await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
        assert r.status_code == 409


class TestPlayingPhase:
    """Tests for the playing phase."""

    async def test_bid_rejected_in_playing(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        await _submit_all_bids(client, game_id, cookies)
        await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
        r = await client.post(
            f"/api/game/{game_id}/bid", json={"player_index": 0, "value": 1}, cookies=cookies
        )
        assert r.status_code == 409

    async def test_enter_round_end_transitions_to_round_end(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        await _submit_all_bids(client, game_id, cookies)
        await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
        r = await client.post(f"/api/game/{game_id}/enter-round-end", cookies=cookies)
        assert r.status_code == 200
        await _assert_phase(client, game_id, cookies, "round_end")


class TestRoundEndPhase:
    """Tests for the round_end phase."""

    async def test_hands_accepted_in_round_end(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        await _submit_all_bids(client, game_id, cookies)
        await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
        await client.post(f"/api/game/{game_id}/enter-round-end", cookies=cookies)
        r = await client.post(
            f"/api/game/{game_id}/hands", json={"player_index": 0, "value": 1}, cookies=cookies
        )
        assert r.status_code == 200

    async def test_end_round_requires_all_hands(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        await _submit_all_bids(client, game_id, cookies)
        await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
        await client.post(f"/api/game/{game_id}/enter-round-end", cookies=cookies)
        # Only 1 hand
        await client.post(
            f"/api/game/{game_id}/hands", json={"player_index": 0, "value": 1}, cookies=cookies
        )
        r = await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)
        assert r.status_code == 400

    async def test_end_round_transitions_to_scoreboard(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        await _play_full_round(client, game_id, cookies)
        await _assert_phase(client, game_id, cookies, "scoreboard")


class TestScoreboardPhase:
    """Tests for the scoreboard phase."""

    async def test_next_round_transitions_to_bidding(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        await _play_full_round(client, game_id, cookies)
        r = await client.post(f"/api/game/{game_id}/next-round", cookies=cookies)
        assert r.status_code == 200
        game = await _assert_phase(client, game_id, cookies, "bidding")
        assert game["current_round"] == 2

    async def test_double_next_round_rejected(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        await _play_full_round(client, game_id, cookies)
        await client.post(f"/api/game/{game_id}/next-round", cookies=cookies)
        r = await client.post(f"/api/game/{game_id}/next-round", cookies=cookies)
        assert r.status_code == 409

    async def test_end_game_from_scoreboard(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        await _play_full_round(client, game_id, cookies)
        r = await client.post(f"/api/game/{game_id}/end", cookies=cookies)
        assert r.status_code == 200
        assert r.json()["status"] == "finished"

    async def test_bid_rejected_in_scoreboard(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        await _play_full_round(client, game_id, cookies)
        r = await client.post(
            f"/api/game/{game_id}/bid", json={"player_index": 0, "value": 1}, cookies=cookies
        )
        assert r.status_code == 409


class TestUndoConsistency:
    """Undo must leave the game in a valid, non-stuck state."""

    async def test_undo_round_1_goes_to_bidding(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        await _play_full_round(client, game_id, cookies)
        r = await client.post(f"/api/game/{game_id}/undo", cookies=cookies)
        assert r.status_code == 200
        game = await _assert_phase(client, game_id, cookies, "bidding")
        assert game["current_round"] == 1

    async def test_undo_round_2_goes_to_scoreboard(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        await _play_full_round(client, game_id, cookies)
        await client.post(f"/api/game/{game_id}/next-round", cookies=cookies)
        await _play_full_round(client, game_id, cookies, bids=[0, 1, 0], hands=[0, 1, 0])
        r = await client.post(f"/api/game/{game_id}/undo", cookies=cookies)
        assert r.status_code == 200
        await _assert_phase(client, game_id, cookies, "scoreboard")

    async def test_undo_then_replay_works(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        await _play_full_round(client, game_id, cookies)
        # Undo
        await client.post(f"/api/game/{game_id}/undo", cookies=cookies)
        await _assert_phase(client, game_id, cookies, "bidding")
        # Replay the round
        await _play_full_round(client, game_id, cookies, bids=[0, 0, 1], hands=[0, 0, 1])
        await _assert_phase(client, game_id, cookies, "scoreboard")

    async def test_undo_with_no_rounds_returns_400(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        r = await client.post(f"/api/game/{game_id}/undo", cookies=cookies)
        assert r.status_code == 400


class TestDealerRotation:
    """Dealer must rotate correctly across rounds."""

    async def test_dealer_starts_at_0(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        game = await _assert_phase(client, game_id, cookies, "bidding")
        assert game["dealer_index"] == 0

    async def test_dealer_rotates_on_next_round(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        await _play_full_round(client, game_id, cookies)
        await client.post(f"/api/game/{game_id}/next-round", cookies=cookies)
        game = await _assert_phase(client, game_id, cookies, "bidding")
        assert game["dealer_index"] == 1

    async def test_dealer_wraps_around(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        # Play 3 rounds (3 players, dealer should wrap to 0)
        for _ in range(3):
            await _play_full_round(client, game_id, cookies, bids=[0, 0, 0], hands=[0, 0, 0])
            await client.post(f"/api/game/{game_id}/next-round", cookies=cookies)
        game = await _assert_phase(client, game_id, cookies, "bidding")
        assert game["dealer_index"] == 0  # wrapped back


class TestEndGameConsistency:
    """End game must be final — no further actions allowed."""

    async def test_end_game_sets_finished(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        await _play_full_round(client, game_id, cookies)
        await client.post(f"/api/game/{game_id}/end", cookies=cookies)
        r = await client.get(f"/api/game/{game_id}", cookies=cookies)
        assert r.json()["status"] == "finished"
        assert r.json()["phase"] == "final"

    async def test_double_end_game_returns_409(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        await _play_full_round(client, game_id, cookies)
        await client.post(f"/api/game/{game_id}/end", cookies=cookies)
        r = await client.post(f"/api/game/{game_id}/end", cookies=cookies)
        assert r.status_code == 409

    async def test_bid_rejected_after_end(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        await _play_full_round(client, game_id, cookies)
        await client.post(f"/api/game/{game_id}/end", cookies=cookies)
        r = await client.post(
            f"/api/game/{game_id}/bid", json={"player_index": 0, "value": 1}, cookies=cookies
        )
        assert r.status_code == 409

    async def test_next_round_rejected_after_end(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)
        await _play_full_round(client, game_id, cookies)
        await client.post(f"/api/game/{game_id}/end", cookies=cookies)
        r = await client.post(f"/api/game/{game_id}/next-round", cookies=cookies)
        assert r.status_code == 409


class TestMultiRoundConsistency:
    """Full multi-round game — verify state never gets stuck."""

    async def test_three_rounds_all_phases_correct(self, client: AsyncClient):
        pg_id, cookies = await _setup(client)
        game_id = await _create_game(client, pg_id, cookies)

        round_bids = [
            [1, 0, 2],
            [0, 1, 0],
            [2, 2, 0],
        ]

        for round_num, bids in enumerate(round_bids, 1):
            # Should be in bidding
            game = await _assert_phase(client, game_id, cookies, "bidding")
            assert game["current_round"] == round_num

            # Play the round
            await _play_full_round(client, game_id, cookies, bids=bids, hands=bids)

            # Should be in scoreboard
            await _assert_phase(client, game_id, cookies, "scoreboard")

            # Scoreboard shows correct round count
            r = await client.get(f"/api/game/{game_id}/scoreboard", cookies=cookies)
            assert len(r.json()["rounds"]) == round_num

            # Advance (except last)
            if round_num < 3:
                await client.post(f"/api/game/{game_id}/next-round", cookies=cookies)

        # End game
        r = await client.post(f"/api/game/{game_id}/end", cookies=cookies)
        assert r.json()["status"] == "finished"

        # Final scoreboard has all 3 rounds
        r = await client.get(f"/api/game/{game_id}/scoreboard", cookies=cookies)
        assert len(r.json()["rounds"]) == 3
