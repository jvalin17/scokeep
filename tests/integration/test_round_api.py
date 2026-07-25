"""Integration tests for round API endpoints.

Tests bid submission, phase enforcement, hands entry,
round scoring, and bid editing.
"""

from httpx import AsyncClient


async def _setup_game(client: AsyncClient) -> dict:
    """Helper: create playground, auth, create game. Return game + cookies."""
    await client.post("/api/playground", json={
        "name": "Round API Test",
        "pin": "1234",
        "players": ["Alice", "Bob", "Charlie", "Dave"],
    })
    auth = await client.post("/api/playground/auth", json={
        "name": "Round API Test",
        "pin": "1234",
    })
    cookies = {"scokeep_session": auth.cookies.get("scokeep_session")}
    pg = auth.json()

    game_resp = await client.post("/api/game", json={
        "playground_id": pg["id"],
        "players": ["Alice", "Bob", "Charlie", "Dave"],
        "settings": {"num_sets": 1},
    }, cookies=cookies)
    game = game_resp.json()
    return {**game, "cookies": cookies}


class TestSubmitBid:

    async def test_submit_bid_returns_200(self, client: AsyncClient):
        game = await _setup_game(client)

        response = await client.post(
            f"/api/game/{game['id']}/bid",
            json={"player_index": 0, "value": 3},
            cookies=game["cookies"],
        )

        assert response.status_code == 200
        body = response.json()
        assert body["bids"]["0"] == 3

    async def test_reject_duplicate_bid(self, client: AsyncClient):
        game = await _setup_game(client)

        await client.post(
            f"/api/game/{game['id']}/bid",
            json={"player_index": 0, "value": 3},
            cookies=game["cookies"],
        )
        response = await client.post(
            f"/api/game/{game['id']}/bid",
            json={"player_index": 0, "value": 2},
            cookies=game["cookies"],
        )

        assert response.status_code == 409


class TestPhaseEnforcement:

    async def test_reject_hands_during_bidding(self, client: AsyncClient):
        game = await _setup_game(client)

        response = await client.post(
            f"/api/game/{game['id']}/hands",
            json={"player_index": 0, "value": 2},
            cookies=game["cookies"],
        )

        assert response.status_code == 409

    async def test_reject_bid_during_play(self, client: AsyncClient):
        game = await _setup_game(client)

        # Submit all 4 bids then confirm
        for i in range(4):
            await client.post(
                f"/api/game/{game['id']}/bid",
                json={"player_index": i, "value": 1},
                cookies=game["cookies"],
            )
        await client.post(
            f"/api/game/{game['id']}/start-round",
            cookies=game["cookies"],
        )

        # Now try to bid — should be rejected
        response = await client.post(
            f"/api/game/{game['id']}/bid",
            json={"player_index": 0, "value": 2},
            cookies=game["cookies"],
        )

        assert response.status_code == 409


class TestConfirmBids:

    async def test_confirm_bids_starts_round(self, client: AsyncClient):
        game = await _setup_game(client)

        for i in range(4):
            await client.post(
                f"/api/game/{game['id']}/bid",
                json={"player_index": i, "value": 1},
                cookies=game["cookies"],
            )

        response = await client.post(
            f"/api/game/{game['id']}/start-round",
            cookies=game["cookies"],
        )

        assert response.status_code == 200
        assert response.json()["phase"] == "playing"

    async def test_reject_confirm_with_missing_bids(self, client: AsyncClient):
        game = await _setup_game(client)

        await client.post(
            f"/api/game/{game['id']}/bid",
            json={"player_index": 0, "value": 1},
            cookies=game["cookies"],
        )

        response = await client.post(
            f"/api/game/{game['id']}/start-round",
            cookies=game["cookies"],
        )

        assert response.status_code == 400


class TestFullRoundLifecycle:

    async def test_bid_confirm_play_hands_score(self, client: AsyncClient):
        """Full round lifecycle: bid → confirm → play → hands → score."""
        game = await _setup_game(client)
        game_id = game["id"]
        cookies = game["cookies"]

        # 1. Submit bids
        bids = [2, 0, 3, 1]
        for i, bid in enumerate(bids):
            resp = await client.post(
                f"/api/game/{game_id}/bid",
                json={"player_index": i, "value": bid},
                cookies=cookies,
            )
            assert resp.status_code == 200

        # 2. Confirm bids → playing
        resp = await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
        assert resp.status_code == 200
        assert resp.json()["phase"] == "playing"

        # 3. End round button → round_end phase
        resp = await client.post(
            f"/api/game/{game_id}/enter-round-end", cookies=cookies
        )
        assert resp.status_code == 200

        # 4. Submit hands won
        hands = [2, 0, 1, 1]
        for i, hand in enumerate(hands):
            resp = await client.post(
                f"/api/game/{game_id}/hands",
                json={"player_index": i, "value": hand},
                cookies=cookies,
            )
            assert resp.status_code == 200

        # 5. End round → scores calculated
        resp = await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)
        assert resp.status_code == 200
        body = resp.json()
        assert body["scores"] == {"0": 20, "1": 10, "2": -30, "3": 11}

        # 6. Game should advance to round 2
        game_resp = await client.get(f"/api/game/{game_id}", cookies=cookies)
        game_state = game_resp.json()
        assert game_state["current_round"] == 2
        assert game_state["phase"] == "bidding"
        assert game_state["dealer_index"] == 1


class TestEditBid:

    async def test_edit_bid_via_api(self, client: AsyncClient):
        game = await _setup_game(client)

        await client.post(
            f"/api/game/{game['id']}/bid",
            json={"player_index": 0, "value": 3},
            cookies=game["cookies"],
        )

        response = await client.patch(
            f"/api/game/{game['id']}/bid/0",
            json={"value": 5},
            cookies=game["cookies"],
        )

        assert response.status_code == 200
        assert response.json()["bids"]["0"] == 5


class TestGetBids:

    async def test_get_bids_returns_all(self, client: AsyncClient):
        game = await _setup_game(client)

        await client.post(
            f"/api/game/{game['id']}/bid",
            json={"player_index": 0, "value": 3},
            cookies=game["cookies"],
        )
        await client.post(
            f"/api/game/{game['id']}/bid",
            json={"player_index": 1, "value": 1},
            cookies=game["cookies"],
        )

        response = await client.get(
            f"/api/game/{game['id']}/bids",
            cookies=game["cookies"],
        )

        assert response.status_code == 200
        body = response.json()
        assert body["bids"] == {"0": 3, "1": 1}
