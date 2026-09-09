"""Full app simulation — plays through every user flow end-to-end.

Simulates a real game session against the API to catch regressions.
Every assertion maps to a requirement from requirements.md.
"""

from httpx import AsyncClient

from app.utils.trump import get_cards_for_round, get_trump_for_round

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def create_playground(client: AsyncClient, name: str, pin: str, players: list[str]):
    """Create playground + auth, return (playground_dict, cookies)."""
    resp = await client.post(
        "/api/playground",
        json={
            "name": name,
            "pin": pin,
            "players": players,
        },
    )
    assert resp.status_code == 201
    playground = resp.json()

    auth = await client.post(
        "/api/playground/auth",
        json={
            "name": name,
            "pin": pin,
        },
    )
    assert auth.status_code == 200
    cookies = {"scokeep_session": auth.cookies.get("scokeep_session")}
    return playground, cookies


async def start_game(client, playground_id, cookies, players, settings=None):
    """Create a game, return game dict."""
    resp = await client.post(
        "/api/game",
        json={
            "playground_id": playground_id,
            "players": players,
            "settings": settings or {},
        },
        cookies=cookies,
    )
    assert resp.status_code == 201
    return resp.json()


async def play_round(client, game_id, cookies, bids, hands):
    """Submit bids, start round, enter round end, submit hands, end round."""
    for player_index, bid in enumerate(bids):
        resp = await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": player_index,
                "value": bid,
            },
            cookies=cookies,
        )
        assert resp.status_code == 200, f"Bid failed for player {player_index}: {resp.text}"

    resp = await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
    assert resp.status_code == 200

    resp = await client.post(f"/api/game/{game_id}/enter-round-end", cookies=cookies)
    assert resp.status_code == 200

    for player_index, hand in enumerate(hands):
        resp = await client.post(
            f"/api/game/{game_id}/hands",
            json={
                "player_index": player_index,
                "value": hand,
            },
            cookies=cookies,
        )
        assert resp.status_code == 200, f"Hands failed for player {player_index}: {resp.text}"

    resp = await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# Playground CRUD (req:89-102)
# ---------------------------------------------------------------------------


class TestPlaygroundLifecycle:
    """req:92-96 — Create, auth, persist, remember players."""

    async def test_create_playground_returns_share_code(self, client: AsyncClient):
        """req:92 — Create playground with name + PIN → share code."""
        resp = await client.post(
            "/api/playground",
            json={
                "name": "Friday Night Cards",
                "pin": "7890",
                "players": ["Ravi", "Priya", "Amit"],
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert len(body["share_code"]) == 4
        assert body["name"] == "Friday Night Cards"
        assert body["players"] == ["Ravi", "Priya", "Amit"]

    async def test_auth_with_correct_pin(self, client: AsyncClient):
        """req:93 — Return to playground with name + PIN."""
        pg, cookies = await create_playground(
            client,
            "Auth Test",
            "1234",
            ["Alice", "Bob"],
        )
        # Cookie should be set
        assert cookies["scokeep_session"] is not None

    async def test_auth_with_wrong_pin_fails(self, client: AsyncClient):
        """req:93 — Wrong PIN should be rejected."""
        await client.post(
            "/api/playground",
            json={
                "name": "Wrong PIN",
                "pin": "1234",
                "players": ["A", "B"],
            },
        )
        resp = await client.post(
            "/api/playground/auth",
            json={
                "name": "Wrong PIN",
                "pin": "9999",
            },
        )
        assert resp.status_code == 401

    async def test_playground_remembers_players(self, client: AsyncClient):
        """req:96 — Playground stores its regular players."""
        pg, cookies = await create_playground(
            client,
            "Remember Players",
            "1234",
            ["Ravi", "Priya", "Amit"],
        )
        resp = await client.get(
            f"/api/playground/{pg['share_code']}",
            cookies=cookies,
        )
        assert resp.status_code == 200
        assert resp.json()["players"] == ["Ravi", "Priya", "Amit"]

    async def test_join_live_game_no_pin(self, client: AsyncClient):
        """req:94,102 — Join by share code without PIN when game active."""
        pg, cookies = await create_playground(
            client,
            "Join Test",
            "1234",
            ["Alice", "Bob"],
        )
        await start_game(client, pg["id"], cookies, ["Alice", "Bob"])

        # Join without PIN
        resp = await client.post(
            f"/api/playground/join/{pg['share_code']}",
        )
        assert resp.status_code == 200

    async def test_join_without_active_game_fails(self, client: AsyncClient):
        """req:102 — No active game → can't join without PIN."""
        pg, cookies = await create_playground(
            client,
            "No Game Join",
            "1234",
            ["Alice", "Bob"],
        )
        resp = await client.post(
            f"/api/playground/join/{pg['share_code']}",
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Game lifecycle + phase transitions (req:75-85)
# ---------------------------------------------------------------------------


class TestGameLifecycle:
    """Full game creation, round play, scoring, and ending."""

    async def test_game_starts_in_bidding_phase(self, client: AsyncClient):
        """req:80 — Game starts in bidding phase."""
        pg, cookies = await create_playground(
            client,
            "Phase Start",
            "1234",
            ["Alice", "Bob", "Charlie"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob", "Charlie"],
        )
        assert game["phase"] == "bidding"
        assert game["current_round"] == 1
        assert game["status"] == "active"

    async def test_full_round_phases(self, client: AsyncClient):
        """req:80-85 — bidding → playing → round_end → scoreboard."""
        pg, cookies = await create_playground(
            client,
            "Phase Flow",
            "1234",
            ["Alice", "Bob"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob"],
        )
        game_id = game["id"]

        # Bidding → submit bids
        for i in range(2):
            await client.post(
                f"/api/game/{game_id}/bid",
                json={
                    "player_index": i,
                    "value": 3,
                },
                cookies=cookies,
            )

        # Start round → playing
        await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
        game_resp = await client.get(f"/api/game/{game_id}", cookies=cookies)
        assert game_resp.json()["phase"] == "playing"

        # Enter round end → round_end
        await client.post(f"/api/game/{game_id}/enter-round-end", cookies=cookies)
        game_resp = await client.get(f"/api/game/{game_id}", cookies=cookies)
        assert game_resp.json()["phase"] == "round_end"

        # Submit hands + end round → scoreboard
        for i in range(2):
            await client.post(
                f"/api/game/{game_id}/hands",
                json={
                    "player_index": i,
                    "value": 4,
                },
                cookies=cookies,
            )
        await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)
        game_resp = await client.get(f"/api/game/{game_id}", cookies=cookies)
        assert game_resp.json()["phase"] == "scoreboard"

    async def test_end_game_from_any_phase(self, client: AsyncClient):
        """req:100 — End game anytime."""
        pg, cookies = await create_playground(
            client,
            "End Any Phase",
            "1234",
            ["Alice", "Bob"],
        )

        # End from bidding
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob"],
        )
        resp = await client.post(f"/api/game/{game['id']}/end", cookies=cookies)
        assert resp.status_code == 200
        assert resp.json()["status"] == "finished"

        # End from playing
        game2 = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob"],
        )
        for i in range(2):
            await client.post(
                f"/api/game/{game2['id']}/bid",
                json={
                    "player_index": i,
                    "value": 1,
                },
                cookies=cookies,
            )
        await client.post(f"/api/game/{game2['id']}/start-round", cookies=cookies)
        resp = await client.post(f"/api/game/{game2['id']}/end", cookies=cookies)
        assert resp.status_code == 200
        assert resp.json()["status"] == "finished"

    async def test_no_active_game_after_end(self, client: AsyncClient):
        """After ending, active game endpoint returns 404."""
        pg, cookies = await create_playground(
            client,
            "Clear Active",
            "1234",
            ["Alice", "Bob"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob"],
        )
        await client.post(f"/api/game/{game['id']}/end", cookies=cookies)

        resp = await client.get(
            f"/api/game/active/{pg['id']}",
            cookies=cookies,
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Bidding rules (req:104-114)
# ---------------------------------------------------------------------------


class TestBiddingRules:
    """Bidding phase validation and must-lose enforcement."""

    async def test_bid_accepts_0_to_cards_dealt(self, client: AsyncClient):
        """req:108 — Keypad 0-8, bid value 0 to cards dealt."""
        pg, cookies = await create_playground(
            client,
            "Bid Range",
            "1234",
            ["Alice", "Bob"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob"],
        )
        game_id = game["id"]
        cards_dealt = get_cards_for_round(1)  # 8

        # Bid 0 works
        resp = await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 0,
                "value": 0,
            },
            cookies=cookies,
        )
        assert resp.status_code == 200

        # Bid 8 works (= cards dealt)
        resp = await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 1,
                "value": cards_dealt,
            },
            cookies=cookies,
        )
        assert resp.status_code == 200

    async def test_overbidding_is_allowed(self, client: AsyncClient):
        """Total bids CAN exceed cards dealt — only must-lose restricts."""
        pg, cookies = await create_playground(
            client,
            "Overbid",
            "1234",
            ["Alice", "Bob", "Charlie"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob", "Charlie"],
            settings={"must_lose": False},
        )
        game_id = game["id"]

        # All bid 8 (total = 24, cards = 8) — should all succeed
        for i in range(3):
            resp = await client.post(
                f"/api/game/{game_id}/bid",
                json={
                    "player_index": i,
                    "value": 8,
                },
                cookies=cookies,
            )
            assert resp.status_code == 200

    async def test_must_lose_blocks_last_player(self, client: AsyncClient):
        """req:113 — Must-lose: last player can't make total = cards dealt."""
        pg, cookies = await create_playground(
            client,
            "Must Lose",
            "1234",
            ["Alice", "Bob", "Charlie"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob", "Charlie"],
            settings={"must_lose": True},
        )
        game_id = game["id"]

        # cards_dealt = 8 for round 1. Alice bids 3, Bob bids 3 → total = 6
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

        # Charlie bidding 2 would make total = 8 = cards dealt → must be blocked
        resp = await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 2,
                "value": 2,
            },
            cookies=cookies,
        )
        assert resp.status_code == 409

        # Charlie bidding 1 should work (total = 7 ≠ 8)
        resp = await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 2,
                "value": 1,
            },
            cookies=cookies,
        )
        assert resp.status_code == 200

    async def test_must_lose_does_not_restrict_non_last_player(self, client: AsyncClient):
        """Non-last players can bid any value in must-lose mode."""
        pg, cookies = await create_playground(
            client,
            "Must Lose Non-Last",
            "1234",
            ["Alice", "Bob", "Charlie"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob", "Charlie"],
            settings={"must_lose": True},
        )
        game_id = game["id"]

        # Alice (first player) bids 8 — all cards. Should succeed.
        resp = await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 0,
                "value": 8,
            },
            cookies=cookies,
        )
        assert resp.status_code == 200

    async def test_edit_bid_works(self, client: AsyncClient):
        """req:112 — Can edit bid before starting round."""
        pg, cookies = await create_playground(
            client,
            "Edit Bid",
            "1234",
            ["Alice", "Bob"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob"],
        )
        game_id = game["id"]

        # Submit bid
        await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 0,
                "value": 3,
            },
            cookies=cookies,
        )

        # Edit bid via PATCH
        resp = await client.patch(
            f"/api/game/{game_id}/bid/0",
            json={
                "value": 5,
            },
            cookies=cookies,
        )
        assert resp.status_code == 200

        # Verify edited value
        bids_resp = await client.get(
            f"/api/game/{game_id}/bids",
            cookies=cookies,
        )
        assert bids_resp.json()["bids"]["0"] == 5

    async def test_edit_bid_then_start_round(self, client: AsyncClient):
        """After editing a bid, start round should still work."""
        pg, cookies = await create_playground(
            client,
            "Edit Then Start",
            "1234",
            ["Alice", "Bob", "Charlie"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob", "Charlie"],
        )
        game_id = game["id"]

        # Submit all bids
        for i in range(3):
            await client.post(
                f"/api/game/{game_id}/bid",
                json={
                    "player_index": i,
                    "value": 2,
                },
                cookies=cookies,
            )

        # Edit player 1's bid
        resp = await client.patch(
            f"/api/game/{game_id}/bid/1",
            json={
                "value": 4,
            },
            cookies=cookies,
        )
        assert resp.status_code == 200

        # Verify edited value
        bids = await client.get(f"/api/game/{game_id}/bids", cookies=cookies)
        assert bids.json()["bids"]["1"] == 4

        # Start round should still work (all bids present)
        resp = await client.post(
            f"/api/game/{game_id}/start-round",
            cookies=cookies,
        )
        assert resp.status_code == 200

    async def test_start_round_requires_all_bids(self, client: AsyncClient):
        """req:112 — Can't start round until all bids are in."""
        pg, cookies = await create_playground(
            client,
            "Incomplete Bids",
            "1234",
            ["Alice", "Bob"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob"],
        )
        game_id = game["id"]

        # Only submit 1 of 2 bids
        await client.post(
            f"/api/game/{game_id}/bid",
            json={
                "player_index": 0,
                "value": 3,
            },
            cookies=cookies,
        )

        # Start round should fail (not all bids submitted)
        resp = await client.post(
            f"/api/game/{game_id}/start-round",
            cookies=cookies,
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Scoring rules (req:125-129)
# ---------------------------------------------------------------------------


class TestScoringRules:
    """Kachuful standard scoring formula verification."""

    async def test_bid_0_made_scores_10(self, client: AsyncClient):
        """req:128 — Bid 0 made = 10 points."""
        pg, cookies = await create_playground(
            client,
            "Score Bid0",
            "1234",
            ["Alice", "Bob"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob"],
        )
        # Alice bids 0, gets 0 → +10. Bob bids 8, gets 8 → +80.
        await play_round(client, game["id"], cookies, [0, 8], [0, 8])

        scoreboard = await client.get(
            f"/api/game/{game['id']}/scoreboard",
            cookies=cookies,
        )
        totals = scoreboard.json()["totals"]
        assert totals["0"] == 10  # Alice: bid 0 made
        assert totals["1"] == 80  # Bob: bid 8 made

    async def test_bid_1_made_scores_11(self, client: AsyncClient):
        """req:128 — Bid 1 made = 11 points."""
        pg, cookies = await create_playground(
            client,
            "Score Bid1",
            "1234",
            ["Alice", "Bob"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob"],
        )
        await play_round(client, game["id"], cookies, [1, 7], [1, 7])

        scoreboard = await client.get(
            f"/api/game/{game['id']}/scoreboard",
            cookies=cookies,
        )
        totals = scoreboard.json()["totals"]
        assert totals["0"] == 11  # Alice: bid 1 made
        assert totals["1"] == 70  # Bob: bid 7 made (7×10)

    async def test_bid_missed_negates_score(self, client: AsyncClient):
        """req:128 — Miss = same value negated."""
        pg, cookies = await create_playground(
            client,
            "Score Miss",
            "1234",
            ["Alice", "Bob"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob"],
        )
        # Alice bids 3, gets 5 (miss → -30). Bob bids 0, gets 3 (miss → -10).
        await play_round(client, game["id"], cookies, [3, 0], [5, 3])

        scoreboard = await client.get(
            f"/api/game/{game['id']}/scoreboard",
            cookies=cookies,
        )
        totals = scoreboard.json()["totals"]
        assert totals["0"] == -30  # Alice: bid 3 missed
        assert totals["1"] == -10  # Bob: bid 0 missed

    async def test_hands_total_must_equal_cards_dealt(self, client: AsyncClient):
        """Hands won must total exactly cards dealt."""
        pg, cookies = await create_playground(
            client,
            "Hands Equal",
            "1234",
            ["Alice", "Bob"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob"],
        )
        # Total hands = 8 = cards dealt (8-card round)
        await play_round(client, game["id"], cookies, [5, 3], [5, 3])

        scoreboard = await client.get(
            f"/api/game/{game['id']}/scoreboard",
            cookies=cookies,
        )
        assert len(scoreboard.json()["rounds"]) == 1


# ---------------------------------------------------------------------------
# Alternating sets + dealer rotation + trump (req:131-151)
# ---------------------------------------------------------------------------


class TestSetsAndRotation:
    """Alternating set direction, dealer rotation, trump rotation."""

    async def test_alternating_set_cards(self, client: AsyncClient):
        """Sets alternate: 8→1, 1→8, 8→1."""
        set1 = [get_cards_for_round(r) for r in range(1, 9)]
        set2 = [get_cards_for_round(r) for r in range(9, 17)]
        set3 = [get_cards_for_round(r) for r in range(17, 25)]
        assert set1 == [8, 7, 6, 5, 4, 3, 2, 1]
        assert set2 == [1, 2, 3, 4, 5, 6, 7, 8]
        assert set3 == [8, 7, 6, 5, 4, 3, 2, 1]

    async def test_set_boundary_transition(self, client: AsyncClient):
        """At set boundary: ...2,1,1,2... (descend→ascend)."""
        cards = [get_cards_for_round(r) for r in range(7, 11)]
        assert cards == [2, 1, 1, 2]

    async def test_test_set_type_4_cards(self, client: AsyncClient):
        """Test set (rounds_per_set=4): 4,3,2,1,1,2,3,4."""
        pg, cookies = await create_playground(
            client,
            "Test Set",
            "1234",
            ["Alice", "Bob"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob"],
            settings={"num_sets": 2, "rounds_per_set": 4},
        )
        assert game["total_rounds"] == 8  # 2 × 4

        cards = [get_cards_for_round(r, 4) for r in range(1, 9)]
        assert cards == [4, 3, 2, 1, 1, 2, 3, 4]

    async def test_trump_rotation(self, client: AsyncClient):
        """req:149 — ♠→♦→♣→♥ repeating."""
        trumps = [get_trump_for_round(r) for r in range(1, 5)]
        assert trumps == ["spades", "diamonds", "clubs", "hearts"]
        # Wraps
        assert get_trump_for_round(5) == "spades"

    async def test_dealer_rotates_each_round(self, client: AsyncClient):
        """req:142 — Dealer rotates clockwise each round."""
        pg, cookies = await create_playground(
            client,
            "Dealer Rotation",
            "1234",
            ["Alice", "Bob", "Charlie"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob", "Charlie"],
        )
        game_id = game["id"]
        assert game["dealer_index"] == 0

        # Play round 1
        await play_round(client, game_id, cookies, [0, 0, 0], [0, 0, 0])

        # Next round
        await client.post(f"/api/game/{game_id}/next-round", cookies=cookies)
        game_resp = await client.get(f"/api/game/{game_id}", cookies=cookies)
        assert game_resp.json()["dealer_index"] == 1

        # Play round 2
        await play_round(client, game_id, cookies, [0, 0, 0], [0, 0, 0])

        # Next round
        await client.post(f"/api/game/{game_id}/next-round", cookies=cookies)
        game_resp = await client.get(f"/api/game/{game_id}", cookies=cookies)
        assert game_resp.json()["dealer_index"] == 2

    async def test_dealer_wraps_around(self, client: AsyncClient):
        """req:142 — Dealer wraps from last player to first."""
        pg, cookies = await create_playground(
            client,
            "Dealer Wrap",
            "1234",
            ["Alice", "Bob"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob"],
        )
        game_id = game["id"]

        # Round 1: dealer 0
        await play_round(client, game_id, cookies, [0, 0], [0, 0])
        await client.post(f"/api/game/{game_id}/next-round", cookies=cookies)

        # Round 2: dealer 1
        game_resp = await client.get(f"/api/game/{game_id}", cookies=cookies)
        assert game_resp.json()["dealer_index"] == 1

        await play_round(client, game_id, cookies, [0, 0], [0, 0])
        await client.post(f"/api/game/{game_id}/next-round", cookies=cookies)

        # Round 3: dealer wraps to 0
        game_resp = await client.get(f"/api/game/{game_id}", cookies=cookies)
        assert game_resp.json()["dealer_index"] == 0


# ---------------------------------------------------------------------------
# Scoreboard + undo (req:153-160)
# ---------------------------------------------------------------------------


class TestScoreboardAndUndo:
    """Scoreboard data and undo functionality."""

    async def test_scoreboard_has_round_data(self, client: AsyncClient):
        """req:156 — Cumulative scores available."""
        pg, cookies = await create_playground(
            client,
            "Scoreboard Data",
            "1234",
            ["Alice", "Bob"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob"],
        )
        await play_round(client, game["id"], cookies, [2, 3], [2, 6])

        resp = await client.get(
            f"/api/game/{game['id']}/scoreboard",
            cookies=cookies,
        )
        body = resp.json()
        assert len(body["rounds"]) == 1
        assert body["rounds"][0]["round_num"] == 1
        assert "0" in body["totals"]
        assert "1" in body["totals"]

    async def test_scoreboard_empty_on_early_end(self, client: AsyncClient):
        """End game with no rounds → empty scoreboard."""
        pg, cookies = await create_playground(
            client,
            "Empty Score",
            "1234",
            ["Alice", "Bob"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob"],
        )
        await client.post(f"/api/game/{game['id']}/end", cookies=cookies)

        resp = await client.get(
            f"/api/game/{game['id']}/scoreboard",
            cookies=cookies,
        )
        body = resp.json()
        assert body["rounds"] == []
        assert all(v == 0 for v in body["totals"].values())

    async def test_undo_last_round(self, client: AsyncClient):
        """req:160 — Undo reverts last round scores."""
        pg, cookies = await create_playground(
            client,
            "Undo Test",
            "1234",
            ["Alice", "Bob"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob"],
        )
        game_id = game["id"]

        await play_round(client, game_id, cookies, [2, 3], [2, 3])

        # Verify scores exist
        sb = await client.get(f"/api/game/{game_id}/scoreboard", cookies=cookies)
        assert sb.json()["totals"]["0"] == 20

        # Undo
        resp = await client.post(f"/api/game/{game_id}/undo", cookies=cookies)
        assert resp.status_code == 200

        # Scores should be zeroed
        sb = await client.get(f"/api/game/{game_id}/scoreboard", cookies=cookies)
        assert sb.json()["totals"]["0"] == 0
        assert sb.json()["rounds"] == []

    async def test_undo_with_no_rounds_fails(self, client: AsyncClient):
        """Can't undo when no rounds have been played."""
        pg, cookies = await create_playground(
            client,
            "Undo Empty",
            "1234",
            ["Alice", "Bob"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob"],
        )
        resp = await client.post(
            f"/api/game/{game['id']}/undo",
            cookies=cookies,
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Multi-round full game simulation
# ---------------------------------------------------------------------------


class TestFullGameSimulation:
    """Play a complete multi-round game and verify all scores."""

    async def test_3_round_game_with_test_set(self, client: AsyncClient):
        """Play 3 rounds with test set (4,3,2) and verify cumulative scores."""
        pg, cookies = await create_playground(
            client,
            "Full Sim",
            "1234",
            ["Ravi", "Priya", "Amit"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Ravi", "Priya", "Amit"],
            settings={"num_sets": 1, "rounds_per_set": 4, "must_lose": False},
        )
        game_id = game["id"]
        assert game["total_rounds"] == 4

        # Round 1 (4 cards): Ravi bids 2 gets 2 (+20),
        # Priya bids 1 gets 1 (+11), Amit bids 0 gets 1 (-10)
        await play_round(client, game_id, cookies, [2, 1, 0], [2, 1, 1])
        await client.post(f"/api/game/{game_id}/next-round", cookies=cookies)

        # Verify round 1 scores
        sb = await client.get(f"/api/game/{game_id}/scoreboard", cookies=cookies)
        totals = sb.json()["totals"]
        assert totals["0"] == 20  # Ravi
        assert totals["1"] == 11  # Priya
        assert totals["2"] == -10  # Amit

        # Round 2 (3 cards): Ravi bids 0 gets 0 (+10),
        # Priya bids 3 gets 2 (-30), Amit bids 1 gets 1 (+11)
        await play_round(client, game_id, cookies, [0, 3, 1], [0, 2, 1])
        await client.post(f"/api/game/{game_id}/next-round", cookies=cookies)

        sb = await client.get(f"/api/game/{game_id}/scoreboard", cookies=cookies)
        totals = sb.json()["totals"]
        assert totals["0"] == 30  # 20 + 10
        assert totals["1"] == -19  # 11 + (-30)
        assert totals["2"] == 1  # -10 + 11

        # Round 3 (2 cards): all bid 1, all get 1
        await play_round(client, game_id, cookies, [1, 1, 0], [1, 1, 0])
        await client.post(f"/api/game/{game_id}/next-round", cookies=cookies)

        sb = await client.get(f"/api/game/{game_id}/scoreboard", cookies=cookies)
        totals = sb.json()["totals"]
        assert totals["0"] == 41  # 30 + 11
        assert totals["1"] == -8  # -19 + 11
        assert totals["2"] == 11  # 1 + 10

        # End game
        await client.post(f"/api/game/{game_id}/end", cookies=cookies)
        game_resp = await client.get(f"/api/game/{game_id}", cookies=cookies)
        assert game_resp.json()["status"] == "finished"

        # Final scoreboard has all 3 rounds
        sb = await client.get(f"/api/game/{game_id}/scoreboard", cookies=cookies)
        assert len(sb.json()["rounds"]) == 3

    async def test_extend_game_adds_rounds(self, client: AsyncClient):
        """req:101,136 — Extend at set end adds another set."""
        pg, cookies = await create_playground(
            client,
            "Extend Game",
            "1234",
            ["Alice", "Bob"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Alice", "Bob"],
            settings={"num_sets": 1, "rounds_per_set": 4},
        )
        game_id = game["id"]
        assert game["total_rounds"] == 4

        # Extend
        # First need to get to scoreboard phase — play a round
        await play_round(client, game_id, cookies, [0, 0], [0, 0])

        resp = await client.post(
            f"/api/game/{game_id}/extend",
            cookies=cookies,
        )
        assert resp.status_code == 200
        assert resp.json()["total_rounds"] == 8  # 4 + 4 (extends by game's rounds_per_set)


# ---------------------------------------------------------------------------
# Security basics
# ---------------------------------------------------------------------------


class TestSecurityBasics:
    """Auth and cross-playground checks."""

    async def test_game_requires_auth(self, client: AsyncClient):
        """All game endpoints require auth cookie."""
        resp = await client.get("/api/game/1")
        assert resp.status_code == 401

    async def test_cross_playground_blocked(self, client: AsyncClient):
        """Can't access game from another playground's session."""
        pg1, cookies1 = await create_playground(
            client,
            "PG One",
            "1234",
            ["Alice", "Bob"],
        )
        pg2, cookies2 = await create_playground(
            client,
            "PG Two",
            "5678",
            ["Charlie", "Dave"],
        )
        game = await start_game(
            client,
            pg1["id"],
            cookies1,
            ["Alice", "Bob"],
        )

        # Try to access pg1's game with pg2's cookies
        resp = await client.get(
            f"/api/game/{game['id']}",
            cookies=cookies2,
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# End game from any phase (BUG-009)
# ---------------------------------------------------------------------------


class TestEndGameFromAnyPhase:
    """BUG-009 — End Game button must work from bidding phase."""

    async def test_end_game_during_bidding_no_bids(self, client: AsyncClient):
        """End game immediately from bidding with zero bids submitted."""
        pg, cookies = await create_playground(
            client,
            "Early Exit Crew",
            "4321",
            ["Nadia", "Carlos", "Wei"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Nadia", "Carlos", "Wei"],
        )
        assert game["phase"] == "bidding"

        resp = await client.post(
            f"/api/game/{game['id']}/end",
            cookies=cookies,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "finished"
        assert body["phase"] == "final"

        # Scoreboard still accessible with zero rounds
        sb = await client.get(
            f"/api/game/{game['id']}/scoreboard",
            cookies=cookies,
        )
        assert sb.status_code == 200
        assert sb.json()["rounds"] == []

    async def test_end_game_during_bidding_partial_bids(self, client: AsyncClient):
        """End game mid-bidding with some bids submitted."""
        pg, cookies = await create_playground(
            client,
            "Partial Bid Exit",
            "9876",
            ["Lena", "Marco"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Lena", "Marco"],
        )
        # Submit only one bid
        resp = await client.post(
            f"/api/game/{game['id']}/bid",
            json={
                "player_index": 0,
                "value": 3,
            },
            cookies=cookies,
        )
        assert resp.status_code == 200

        # End game with partial bids
        resp = await client.post(
            f"/api/game/{game['id']}/end",
            cookies=cookies,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "finished"

    async def test_end_game_during_bidding_all_bids(self, client: AsyncClient):
        """End game after all bids submitted but before starting round."""
        pg, cookies = await create_playground(
            client,
            "Full Bid Exit",
            "5555",
            ["Anya", "Riku"],
        )
        game = await start_game(
            client,
            pg["id"],
            cookies,
            ["Anya", "Riku"],
        )
        # Submit all bids
        for i in range(2):
            await client.post(
                f"/api/game/{game['id']}/bid",
                json={
                    "player_index": i,
                    "value": 2,
                },
                cookies=cookies,
            )

        # End game from confirm screen
        resp = await client.post(
            f"/api/game/{game['id']}/end",
            cookies=cookies,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "finished"
