"""Regression test: end-round must succeed on every round of a multi-round game.

Bug: expire_on_commit=False caused stale JSONB reads on hands_won,
making end-round return 400 on later rounds despite all hands submitted.
"""

from httpx import AsyncClient


async def _setup_game(client: AsyncClient, player_count: int = 5):
    """Create playground, auth, create game, return (game_id, cookies)."""
    name = f"EndRound Regression {player_count}p"
    await client.post(
        "/api/playground",
        json={
            "name": name,
            "pin": "1234",
            "players": [f"P{i}" for i in range(player_count)],
        },
    )
    auth = await client.post(
        "/api/playground/auth",
        json={"name": name, "pin": "1234"},
    )
    cookies = {"scokeep_session": auth.cookies.get("scokeep_session")}
    game_resp = await client.post(
        "/api/game",
        json={
            "playground_id": auth.json()["id"],
            "players": [f"P{i}" for i in range(player_count)],
            "settings": {"num_sets": 1, "rounds_per_set": 8},
        },
        cookies=cookies,
    )
    assert game_resp.status_code == 201
    return game_resp.json()["id"], cookies


async def _play_one_round(client: AsyncClient, game_id: int, cookies: dict, player_count: int):
    """Play a full round: bid → start → enter-round-end → hands → end-round.

    Returns the end-round response for assertion.
    """
    # Bid: everyone bids 1
    for i in range(player_count):
        resp = await client.post(
            f"/api/game/{game_id}/bid",
            json={"player_index": i, "value": 1},
            cookies=cookies,
        )
        assert resp.status_code == 200, f"bid player {i} failed: {resp.text}"

    # Start round
    resp = await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
    assert resp.status_code == 200, f"start-round failed: {resp.text}"

    # Enter round end
    resp = await client.post(f"/api/game/{game_id}/enter-round-end", cookies=cookies)
    assert resp.status_code == 200, f"enter-round-end failed: {resp.text}"

    # Submit hands: first player won 1, rest won 0
    # Total must equal cards_dealt — get it from game state
    game_resp = await client.get(f"/api/game/{game_id}", cookies=cookies)
    game = game_resp.json()
    cards_dealt = _cards_for_round(game["current_round"], game["settings"].get("rounds_per_set", 8))

    for i in range(player_count):
        value = min(cards_dealt, 1) if i == 0 else 0
        resp = await client.post(
            f"/api/game/{game_id}/hands",
            json={"player_index": i, "value": value},
            cookies=cookies,
        )
        assert resp.status_code == 200, f"hands player {i} failed: {resp.text}"
    # Adjust: if cards_dealt > 1, remaining cards go unaccounted.
    # Actually, let's just set hands so total = cards_dealt.
    # P0 gets all the cards.
    # Re-submit P0 with cards_dealt value
    if cards_dealt > 1:
        resp = await client.post(
            f"/api/game/{game_id}/hands",
            json={"player_index": 0, "value": cards_dealt},
            cookies=cookies,
        )
        assert resp.status_code == 200, f"hands P0 re-submit failed: {resp.text}"

    # End round — THIS is what was failing
    end_resp = await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)
    return end_resp


def _cards_for_round(round_num: int, rounds_per_set: int) -> int:
    """Mirror the getRoundCards logic."""
    position_in_set = ((round_num - 1) % rounds_per_set) + 1
    return rounds_per_set - position_in_set + 1


class TestEndRoundMultiRound:
    """Regression: end-round must succeed on every round, not just early ones."""

    async def test_end_round_succeeds_all_rounds_5_players(self, client: AsyncClient):
        """Play 4 rounds with 5 players. end-round must return 200 on every round."""
        player_count = 5
        game_id, cookies = await _setup_game(client, player_count)

        for round_num in range(1, 5):
            end_resp = await _play_one_round(client, game_id, cookies, player_count)
            assert end_resp.status_code == 200, (
                f"end-round FAILED on round {round_num}: {end_resp.status_code} {end_resp.text}"
            )
            # Advance to next round
            if round_num < 4:
                next_resp = await client.post(f"/api/game/{game_id}/next-round", cookies=cookies)
                assert next_resp.status_code == 200

    async def test_end_round_succeeds_all_rounds_3_players(self, client: AsyncClient):
        """Play 4 rounds with 3 players. end-round must return 200 on every round."""
        player_count = 3
        game_id, cookies = await _setup_game(client, player_count)

        for round_num in range(1, 5):
            end_resp = await _play_one_round(client, game_id, cookies, player_count)
            assert end_resp.status_code == 200, (
                f"end-round FAILED on round {round_num}: {end_resp.status_code} {end_resp.text}"
            )
            if round_num < 4:
                next_resp = await client.post(f"/api/game/{game_id}/next-round", cookies=cookies)
                assert next_resp.status_code == 200
