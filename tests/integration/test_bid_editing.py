"""Integration tests for bid editing and navigation.

Tests the backend API flows that support:
- Editing bids via PATCH after initial submission
- Navigating back and re-entering bids
- Must-lose constraint recalculation after edits
"""

from httpx import AsyncClient


async def _setup(client: AsyncClient, name: str, players: list[str]):
    """Create playground + auth, return (playground, cookies)."""
    await client.post(
        "/api/playground",
        json={
            "name": name,
            "pin": "1234",
            "players": players,
        },
    )
    auth = await client.post(
        "/api/playground/auth",
        json={
            "name": name,
            "pin": "1234",
        },
    )
    cookies = {"scokeep_session": auth.cookies.get("scokeep_session")}
    return auth.json(), cookies


async def _create_game(client, pg_id, cookies, players, must_lose=False):
    """Create game with given players and must_lose setting."""
    resp = await client.post(
        "/api/game",
        json={
            "playground_id": pg_id,
            "players": players,
            "settings": {"must_lose": must_lose},
        },
        cookies=cookies,
    )
    assert resp.status_code == 201
    return resp.json()


class TestBidEditViaPatch:
    """Editing existing bids via PATCH — simulates back-navigation flow."""

    async def test_patch_bid_after_submit(self, client: AsyncClient):
        """Submit bid via POST, then change it via PATCH."""
        pg, cookies = await _setup(client, "Patch After Submit", ["Alice", "Bob"])
        game = await _create_game(client, pg["id"], cookies, ["Alice", "Bob"])
        game_id = game["id"]

        # Submit Alice's bid
        resp = await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 0,
                "value": 3,
            },
            cookies=cookies,
        )
        assert resp.status_code == 200

        # Edit Alice's bid via PATCH (simulates going back and changing)
        resp = await client.patch(
            f"/api/game/{game_id}/bid/0",
            json={
                "value": 5,
            },
            cookies=cookies,
        )
        assert resp.status_code == 200

        # Verify the value changed
        bids = await client.get(f"/api/game/{game_id}/bids", cookies=cookies)
        assert bids.json()["bids"]["0"] == 5

    async def test_post_same_player_twice_fails(self, client: AsyncClient):
        """POST bid for same player twice returns 409 — must use PATCH."""
        pg, cookies = await _setup(client, "Double Post", ["Alice", "Bob"])
        game = await _create_game(client, pg["id"], cookies, ["Alice", "Bob"])
        game_id = game["id"]

        # First POST succeeds
        resp = await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 0,
                "value": 3,
            },
            cookies=cookies,
        )
        assert resp.status_code == 200

        # Second POST for same player fails
        resp = await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 0,
                "value": 5,
            },
            cookies=cookies,
        )
        assert resp.status_code == 409

    async def test_edit_multiple_players_then_start(self, client: AsyncClient):
        """Submit all bids, edit two of them via PATCH, then start round."""
        pg, cookies = await _setup(
            client,
            "Edit Multiple",
            ["Alice", "Bob", "Charlie"],
        )
        game = await _create_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob", "Charlie"],
        )
        game_id = game["id"]

        # Submit all bids
        for i, bid in enumerate([2, 3, 1]):
            await client.post(
                f"/api/game/{game_id}/bid",
                json={
                    "player_index": i,
                    "value": bid,
                },
                cookies=cookies,
            )

        # Edit Alice (0) and Charlie (2) via PATCH
        await client.patch(
            f"/api/game/{game_id}/bid/0",
            json={
                "value": 4,
            },
            cookies=cookies,
        )
        await client.patch(
            f"/api/game/{game_id}/bid/2",
            json={
                "value": 0,
            },
            cookies=cookies,
        )

        # Verify
        bids = await client.get(f"/api/game/{game_id}/bids", cookies=cookies)
        assert bids.json()["bids"] == {"0": 4, "1": 3, "2": 0}

        # Start round should work
        resp = await client.post(
            f"/api/game/{game_id}/start-round",
            cookies=cookies,
        )
        assert resp.status_code == 200


class TestMustLoseWithEdits:
    """Must-lose constraint recalculation after bid edits."""

    async def test_must_lose_blocks_forbidden_value(self, client: AsyncClient):
        """Last player can't bid the value that makes total = cards dealt."""
        pg, cookies = await _setup(
            client,
            "Must Lose Basic",
            ["Alice", "Bob", "Charlie"],
        )
        game = await _create_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob", "Charlie"],
            must_lose=True,
        )
        game_id = game["id"]
        # cards dealt = 8 for round 1

        # Alice bids 3, Bob bids 3 → total = 6
        await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 0,
                "value": 3,
            },
            cookies=cookies,
        )
        await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 1,
                "value": 3,
            },
            cookies=cookies,
        )

        # Charlie bidding 2 would make total = 8 = cards dealt → blocked
        resp = await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 2,
                "value": 2,
            },
            cookies=cookies,
        )
        assert resp.status_code == 409

        # Charlie bidding 1 works (total = 7 ≠ 8)
        resp = await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 2,
                "value": 1,
            },
            cookies=cookies,
        )
        assert resp.status_code == 200

    async def test_edit_shifts_forbidden_value(self, client: AsyncClient):
        """After editing a non-last player, the forbidden value for last player changes."""
        pg, cookies = await _setup(
            client,
            "Must Lose Shift",
            ["Alice", "Bob", "Charlie"],
        )
        game = await _create_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob", "Charlie"],
            must_lose=True,
        )
        game_id = game["id"]

        # Alice=3, Bob=3, Charlie=1 (total=7, forbidden was 2)
        await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 0,
                "value": 3,
            },
            cookies=cookies,
        )
        await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 1,
                "value": 3,
            },
            cookies=cookies,
        )
        await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 2,
                "value": 1,
            },
            cookies=cookies,
        )

        # Edit Bob from 3 to 4 → total others = 3+4 = 7
        await client.patch(
            f"/api/game/{game_id}/bid/1",
            json={
                "value": 4,
            },
            cookies=cookies,
        )

        # Now Charlie's bid of 1 makes total = 3+4+1 = 8 = cards dealt
        # Charlie needs to change — edit to 0 (total = 7)
        resp = await client.patch(
            f"/api/game/{game_id}/bid/2",
            json={
                "value": 0,
            },
            cookies=cookies,
        )
        assert resp.status_code == 200

        # Verify final state and start round
        bids = await client.get(f"/api/game/{game_id}/bids", cookies=cookies)
        assert bids.json()["bids"] == {"0": 3, "1": 4, "2": 0}

        resp = await client.post(
            f"/api/game/{game_id}/start-round",
            cookies=cookies,
        )
        assert resp.status_code == 200

    async def test_edit_non_last_player_no_restriction(self, client: AsyncClient):
        """Non-last players have no must-lose restriction, even after edits."""
        pg, cookies = await _setup(
            client,
            "Must Lose Non-Last",
            ["Alice", "Bob", "Charlie"],
        )
        game = await _create_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob", "Charlie"],
            must_lose=True,
        )
        game_id = game["id"]

        # Submit all bids
        await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 0,
                "value": 3,
            },
            cookies=cookies,
        )
        await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 1,
                "value": 3,
            },
            cookies=cookies,
        )
        await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 2,
                "value": 1,
            },
            cookies=cookies,
        )

        # Edit Alice (non-last) to 8 — no restriction
        resp = await client.patch(
            f"/api/game/{game_id}/bid/0",
            json={
                "value": 8,
            },
            cookies=cookies,
        )
        assert resp.status_code == 200
        assert (
            await client.get(
                f"/api/game/{game_id}/bids",
                cookies=cookies,
            )
        ).json()["bids"]["0"] == 8


class TestHandsWonValidation:
    """Hands won values must not exceed remaining cards."""

    async def test_hands_cannot_exceed_cards_dealt(self, client: AsyncClient):
        """Individual hand value cannot exceed cards dealt."""
        pg, cookies = await _setup(client, "Hands Max", ["Alice", "Bob"])
        game = await _create_game(client, pg["id"], cookies, ["Alice", "Bob"])
        game_id = game["id"]

        # Bid and start round (7-card round for round 2 of standard set)
        for i in range(2):
            await client.post(
                f"/api/game/{game_id}/bid",
                json={
                    "player_index": i,
                    "value": 3,
                },
                cookies=cookies,
            )
        await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
        await client.post(f"/api/game/{game_id}/enter-round-end", cookies=cookies)

        # Round 1 has 8 cards. Submitting 9 should fail.
        resp = await client.post(
            f"/api/game/{game_id}/hands",
            json={
                "player_index": 0,
                "value": 9,
            },
            cookies=cookies,
        )
        assert resp.status_code == 409

    async def test_hands_cannot_exceed_remaining(self, client: AsyncClient):
        """After Alice takes 7 of 8, Bob can take at most 1."""
        pg, cookies = await _setup(client, "Hands Remaining", ["Alice", "Bob"])
        game = await _create_game(client, pg["id"], cookies, ["Alice", "Bob"])
        game_id = game["id"]

        for i in range(2):
            await client.post(
                f"/api/game/{game_id}/bid",
                json={
                    "player_index": i,
                    "value": 3,
                },
                cookies=cookies,
            )
        await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
        await client.post(f"/api/game/{game_id}/enter-round-end", cookies=cookies)

        # Alice takes 7 of 8 cards
        await client.post(
            f"/api/game/{game_id}/hands",
            json={
                "player_index": 0,
                "value": 7,
            },
            cookies=cookies,
        )

        # Bob taking 2 would make total 9 > 8 → should fail
        resp = await client.post(
            f"/api/game/{game_id}/hands",
            json={
                "player_index": 1,
                "value": 2,
            },
            cookies=cookies,
        )
        assert resp.status_code == 409

        # Bob taking 1 should succeed (total = 8)
        resp = await client.post(
            f"/api/game/{game_id}/hands",
            json={
                "player_index": 1,
                "value": 1,
            },
            cookies=cookies,
        )
        assert resp.status_code == 200

    async def test_hands_zero_always_allowed(self, client: AsyncClient):
        """0 hands is always a valid entry."""
        pg, cookies = await _setup(client, "Hands Zero", ["Alice", "Bob"])
        game = await _create_game(client, pg["id"], cookies, ["Alice", "Bob"])
        game_id = game["id"]

        for i in range(2):
            await client.post(
                f"/api/game/{game_id}/bid",
                json={
                    "player_index": i,
                    "value": 0,
                },
                cookies=cookies,
            )
        await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
        await client.post(f"/api/game/{game_id}/enter-round-end", cookies=cookies)

        # Alice takes 8 (all cards)
        await client.post(
            f"/api/game/{game_id}/hands",
            json={
                "player_index": 0,
                "value": 8,
            },
            cookies=cookies,
        )

        # Bob takes 0 — always valid
        resp = await client.post(
            f"/api/game/{game_id}/hands",
            json={
                "player_index": 1,
                "value": 0,
            },
            cookies=cookies,
        )
        assert resp.status_code == 200


class TestBidNavigationFlow:
    """Full back-and-forth navigation flow."""

    async def test_submit_go_back_change_go_forward(self, client: AsyncClient):
        """Submit 3 bids, go back to player 1, change, go forward, start round."""
        pg, cookies = await _setup(
            client,
            "Nav Flow",
            ["Alice", "Bob", "Charlie"],
        )
        game = await _create_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob", "Charlie"],
        )
        game_id = game["id"]

        # Submit all 3 bids via POST
        for i, bid in enumerate([2, 3, 4]):
            await client.post(
                f"/api/game/{game_id}/bid",
                json={
                    "player_index": i,
                    "value": bid,
                },
                cookies=cookies,
            )

        # "Go back" to Bob — change bid via PATCH
        resp = await client.patch(
            f"/api/game/{game_id}/bid/1",
            json={
                "value": 5,
            },
            cookies=cookies,
        )
        assert resp.status_code == 200

        # "Go forward" past Charlie (no change needed) — just verify bids
        bids = await client.get(f"/api/game/{game_id}/bids", cookies=cookies)
        assert bids.json()["bids"] == {"0": 2, "1": 5, "2": 4}

        # Start round
        resp = await client.post(
            f"/api/game/{game_id}/start-round",
            cookies=cookies,
        )
        assert resp.status_code == 200

    async def test_edit_all_bids_via_patch(self, client: AsyncClient):
        """Edit every player's bid after initial submission."""
        pg, cookies = await _setup(
            client,
            "Edit All",
            ["Alice", "Bob"],
        )
        game = await _create_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob"],
        )
        game_id = game["id"]

        # Initial bids
        await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 0,
                "value": 1,
            },
            cookies=cookies,
        )
        await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 1,
                "value": 1,
            },
            cookies=cookies,
        )

        # Edit both via PATCH
        await client.patch(
            f"/api/game/{game_id}/bid/0",
            json={
                "value": 7,
            },
            cookies=cookies,
        )
        await client.patch(
            f"/api/game/{game_id}/bid/1",
            json={
                "value": 6,
            },
            cookies=cookies,
        )

        bids = await client.get(f"/api/game/{game_id}/bids", cookies=cookies)
        assert bids.json()["bids"] == {"0": 7, "1": 6}

        # Start round works
        resp = await client.post(
            f"/api/game/{game_id}/start-round",
            cookies=cookies,
        )
        assert resp.status_code == 200
