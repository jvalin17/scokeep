"""GET /api/playground/{share_code}/stats?game_type=… isolation."""

from httpx import AsyncClient


async def _setup(client: AsyncClient, name: str = "Stats Filter Room"):
    await client.post(
        "/api/playground",
        json={"name": name, "pin": "1234", "players": ["Alice", "Bob"]},
    )
    auth = await client.post(
        "/api/playground/auth",
        json={"name": name, "pin": "1234"},
    )
    cookies = {"scokeep_session": auth.cookies.get("scokeep_session")}
    return auth.json(), cookies


async def _finish_judgement(client, pg_id, cookies, players):
    game_resp = await client.post(
        "/api/game",
        json={
            "playground_id": pg_id,
            "players": players,
            "settings": {"num_sets": 1, "game_type": "kachuful"},
        },
        cookies=cookies,
    )
    game_id = game_resp.json()["id"]
    for i, bid in enumerate([1, 1]):
        await client.post(
            f"/api/game/{game_id}/bid",
            json={"player_index": i, "value": bid},
            cookies=cookies,
        )
    await client.post(f"/api/game/{game_id}/start-round", cookies=cookies)
    await client.post(f"/api/game/{game_id}/enter-round-end", cookies=cookies)
    for i, hand in enumerate([1, 1]):
        await client.post(
            f"/api/game/{game_id}/hands",
            json={"player_index": i, "value": hand},
            cookies=cookies,
        )
    await client.post(f"/api/game/{game_id}/end-round", cookies=cookies)
    await client.post(f"/api/game/{game_id}/end", cookies=cookies)
    await client.post(f"/api/game/{game_id}/confirm-final", cookies=cookies)
    return game_id


async def _finish_scoresheet(client, pg_id, cookies, players, label="Declare"):
    game_resp = await client.post(
        "/api/game",
        json={
            "playground_id": pg_id,
            "players": players,
            "settings": {
                "game_type": "scoresheet",
                "winner": "highest",
                "show_totals": True,
                "label": label,
            },
        },
        cookies=cookies,
    )
    assert game_resp.status_code == 201, game_resp.text
    game_id = game_resp.json()["id"]
    sync = await client.post(
        f"/api/game/{game_id}/sync-round",
        json={
            "round_num": 1,
            "cards_dealt": 0,
            "trump_suit": "n/a",
            "bids": {},
            "hands_won": {},
            "scores": {"0": 20, "1": 10},
            "status": "scored",
        },
        cookies=cookies,
    )
    assert sync.status_code == 200, sync.text
    state = await client.post(
        f"/api/game/{game_id}/sync-state",
        json={
            "phase": "review",
            "current_round": 1,
            "dealer_index": 0,
            "status": "finished",
        },
        cookies=cookies,
    )
    assert state.status_code == 200, state.text
    return game_id


async def test_stats_filter_scoresheet_excludes_judgement(client: AsyncClient):
    pg, cookies = await _setup(client, "Filter SS")
    players = ["Alice", "Bob"]
    j_id = await _finish_judgement(client, pg["id"], cookies, players)
    s_id = await _finish_scoresheet(client, pg["id"], cookies, players, label="Mini golf")

    resp = await client.get(
        f"/api/playground/{pg['share_code']}/stats?game_type=scoresheet",
        cookies=cookies,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_games"] == 1
    ids = {g["game_id"] for g in body["game_history"]}
    assert s_id in ids
    assert j_id not in ids
    assert body["game_history"][0]["game_type"] == "scoresheet"
    assert body["game_history"][0]["label"] == "Mini golf"
    assert body["highlights"].get("last_game") is None


async def test_stats_filter_judgement_excludes_scoresheet(client: AsyncClient):
    pg, cookies = await _setup(client, "Filter KJ")
    players = ["Alice", "Bob"]
    j_id = await _finish_judgement(client, pg["id"], cookies, players)
    s_id = await _finish_scoresheet(client, pg["id"], cookies, players)

    resp = await client.get(
        f"/api/playground/{pg['share_code']}/stats?game_type=kachuful",
        cookies=cookies,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_games"] == 1
    ids = {g["game_id"] for g in body["game_history"]}
    assert j_id in ids
    assert s_id not in ids
    assert body["game_history"][0]["game_type"] == "kachuful"


async def test_stats_filter_all_includes_both(client: AsyncClient):
    pg, cookies = await _setup(client, "Filter All")
    players = ["Alice", "Bob"]
    j_id = await _finish_judgement(client, pg["id"], cookies, players)
    s_id = await _finish_scoresheet(client, pg["id"], cookies, players)

    for query in ("", "?game_type=all"):
        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats{query}",
            cookies=cookies,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total_games"] == 2
        ids = {g["game_id"] for g in body["game_history"]}
        assert ids == {j_id, s_id}


async def test_stats_filter_invalid_game_type_422(client: AsyncClient):
    pg, cookies = await _setup(client, "Filter Bad")
    resp = await client.get(
        f"/api/playground/{pg['share_code']}/stats?game_type=rummy",
        cookies=cookies,
    )
    assert resp.status_code == 422


async def test_stats_filter_empty_typed_no_leaked_highlights(client: AsyncClient):
    """Scoresheet filter with only Judgement games returns empty highlights."""
    pg, cookies = await _setup(client, "Filter Empty SS")
    await _finish_judgement(client, pg["id"], cookies, ["Alice", "Bob"])
    resp = await client.get(
        f"/api/playground/{pg['share_code']}/stats?game_type=scoresheet",
        cookies=cookies,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_games"] == 0
    assert body["game_history"] == []
    career = body["highlights"]["career"]
    assert career["sniper"] == []
    assert body["highlights"]["last_game"] is None


async def test_stats_route_game_type_query_matrix(client: AsyncClient):
    """Route accepts each allowed game_type and rejects unknown values."""
    pg, cookies = await _setup(client, "Filter Matrix")
    players = ["Alice", "Bob"]
    await _finish_judgement(client, pg["id"], cookies, players)
    await _finish_scoresheet(client, pg["id"], cookies, players, label="Declare")

    for game_type, expected_total in (("all", 2), ("kachuful", 1), ("scoresheet", 1)):
        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats",
            params={"game_type": game_type},
            cookies=cookies,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total_games"] == expected_total
        assert "game_history" in body
        assert "highlights" in body
        for entry in body["game_history"]:
            assert "game_type" in entry
            assert "label" in entry
            if game_type != "all":
                assert entry["game_type"] == game_type

    bad = await client.get(
        f"/api/playground/{pg['share_code']}/stats",
        params={"game_type": "poker"},
        cookies=cookies,
    )
    assert bad.status_code == 422
