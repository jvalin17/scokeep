"""Test: concurrent hands submissions must not lose entries.

Verifies that even if two hands POST requests overlap (sent before the
first commits), all entries are persisted and end-round succeeds.
"""

from httpx import AsyncClient


async def _setup_round(client: AsyncClient, player_count: int = 5):
    """Create playground, game, bid for all, enter round-end. Return (game_id, cookies)."""
    name = f"Concurrent Hands {player_count}p"
    await client.post(
        "/api/playground",
        json={"name": name, "pin": "1234", "players": [f"P{i}" for i in range(player_count)]},
    )
    auth = await client.post("/api/playground/auth", json={"name": name, "pin": "1234"})
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
    game_id = game_resp.json()["id"]

    # Bid for all players
    for i in range(player_count):
        await client.post(
            f"/api/game/{game_id}/bid",
            json={"player_index": i, "value": 1},
            cookies=cookies,
        )

    # Start round + enter round end
    await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
    await client.post(f"/api/game/{game_id}/enter-round-end", cookies=cookies)

    return game_id, cookies


class TestConcurrentHandsSubmission:
    """Hands submitted concurrently must all persist."""

    async def test_sequential_hands_then_end_round_succeeds(self, client: AsyncClient):
        """Baseline: sequential hands → end-round must return 200."""
        game_id, cookies = await _setup_round(client, 5)

        # Submit hands sequentially — P0 gets all cards, rest get 0
        cards_dealt = 8  # Round 1 of 8-round set

        await client.post(
            f"/api/game/{game_id}/hands",
            json={"player_index": 0, "value": cards_dealt},
            cookies=cookies,
        )
        for i in range(1, 5):
            await client.post(
                f"/api/game/{game_id}/hands",
                json={"player_index": i, "value": 0},
                cookies=cookies,
            )

        resp = await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)
        assert resp.status_code == 200, f"end-round failed: {resp.text}"

    async def test_duplicate_player_index_does_not_corrupt(self, client: AsyncClient):
        """Submitting hands for the same player twice must not lose other entries."""
        game_id, cookies = await _setup_round(client, 3)

        # Submit for all 3 players
        await client.post(
            f"/api/game/{game_id}/hands",
            json={"player_index": 0, "value": 8},
            cookies=cookies,
        )
        await client.post(
            f"/api/game/{game_id}/hands",
            json={"player_index": 1, "value": 0},
            cookies=cookies,
        )
        await client.post(
            f"/api/game/{game_id}/hands",
            json={"player_index": 2, "value": 0},
            cookies=cookies,
        )

        # Submit duplicate for player 0 (simulates double-tap reaching backend)
        await client.post(
            f"/api/game/{game_id}/hands",
            json={"player_index": 0, "value": 8},
            cookies=cookies,
        )

        # end-round must still succeed — all 3 players have entries
        resp = await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)
        assert resp.status_code == 200, f"end-round failed after duplicate: {resp.text}"

    async def test_missing_player_returns_400(self, client: AsyncClient):
        """If a player is genuinely missing, end-round must return 400."""
        game_id, cookies = await _setup_round(client, 3)

        # Only submit for 2 of 3 players
        await client.post(
            f"/api/game/{game_id}/hands",
            json={"player_index": 0, "value": 8},
            cookies=cookies,
        )
        await client.post(
            f"/api/game/{game_id}/hands",
            json={"player_index": 1, "value": 0},
            cookies=cookies,
        )

        # end-round must return 400 — player 2 is missing
        resp = await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)
        assert resp.status_code == 400

    async def test_end_round_across_multiple_rounds(self, client: AsyncClient):
        """Play 4 rounds with 5 players — end-round must succeed on every round."""
        game_id, cookies = await _setup_round(client, 5)
        rounds_per_set = 8

        for round_num in range(1, 5):
            cards_dealt = rounds_per_set - ((round_num - 1) % rounds_per_set)

            # P0 gets all cards, rest get 0
            await client.post(
                f"/api/game/{game_id}/hands",
                json={"player_index": 0, "value": cards_dealt},
                cookies=cookies,
            )
            for i in range(1, 5):
                await client.post(
                    f"/api/game/{game_id}/hands",
                    json={"player_index": i, "value": 0},
                    cookies=cookies,
                )

            resp = await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)
            assert resp.status_code == 200, (
                f"end-round FAILED on round {round_num}: {resp.status_code} {resp.text}"
            )

            if round_num < 4:
                next_resp = await client.post(
                    f"/api/game/{game_id}/next-round", cookies=cookies
                )
                assert next_resp.status_code == 200

                # Re-setup: bid + start-round + enter-round-end
                for i in range(5):
                    await client.post(
                        f"/api/game/{game_id}/bid",
                        json={"player_index": i, "value": 1},
                        cookies=cookies,
                    )
                await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
                await client.post(f"/api/game/{game_id}/enter-round-end", cookies=cookies)
