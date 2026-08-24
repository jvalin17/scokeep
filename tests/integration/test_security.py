"""Security tests — XSS prevention and cross-playground authorization.

BUG-002: XSS via player names — names must be HTML-escaped server-side
BUG-003: Cross-playground auth — user authed to playground A must NOT access games in playground B
"""

from httpx import AsyncClient


async def _create_playground_and_auth(
    client: AsyncClient,
    name: str,
    pin: str = "1234",
    players: list[str] | None = None,
):
    """Create playground, auth, return (playground_dict, cookies)."""
    players = players or ["Alice", "Bob", "Charlie"]
    await client.post(
        "/api/playground",
        json={
            "name": name,
            "pin": pin,
            "players": players,
        },
    )
    auth = await client.post(
        "/api/playground/auth",
        json={
            "name": name,
            "pin": pin,
        },
    )
    cookies = {"scokeep_session": auth.cookies.get("scokeep_session")}
    return auth.json(), cookies


async def _create_game(
    client: AsyncClient,
    playground_id: int,
    cookies: dict,
    players: list[str] | None = None,
):
    """Create a game and return the game dict."""
    players = players or ["Alice", "Bob", "Charlie"]
    resp = await client.post(
        "/api/game",
        json={
            "playground_id": playground_id,
            "players": players,
            "settings": {"num_sets": 1},
        },
        cookies=cookies,
    )
    return resp.json()


class TestXSSPrevention:
    """BUG-002: Player names with HTML/script must be escaped in API responses."""

    async def test_html_in_player_name_is_escaped_in_response(self, client: AsyncClient):
        """API should escape player names containing HTML tags."""
        xss_name = "<img onerror=alert(1) src=x>"
        pg, cookies = await _create_playground_and_auth(
            client,
            "XSS Test",
            players=[xss_name, "Bob", "Charlie"],
        )

        # The stored name should be sanitized
        resp = await client.get(
            f"/api/playground/{pg['share_code']}",
            cookies=cookies,
        )
        assert resp.status_code == 200
        returned_names = resp.json()["players"]
        # Must NOT contain raw < or > — must be escaped
        for name in returned_names:
            assert "<" not in name, f"Raw HTML in player name: {name}"
            assert ">" not in name, f"Raw HTML in player name: {name}"

    async def test_script_tag_in_player_name_is_escaped(self, client: AsyncClient):
        """Script tags must be stripped/escaped."""
        xss_name = '<script>alert("xss")</script>'
        pg, cookies = await _create_playground_and_auth(
            client,
            "XSS Script Test",
            players=[xss_name, "Bob"],
        )

        game = await _create_game(client, pg["id"], cookies, players=[xss_name, "Bob"])
        # Player names in game response must be clean
        for name in game["players"]:
            assert "<script>" not in name, f"Script tag in player name: {name}"


    async def test_html_in_playground_name_is_escaped(self, client: AsyncClient):
        """Playground names with HTML must be escaped — defense at input boundary."""
        xss_name = '<img onerror=alert(1) src=x>'
        pg, cookies = await _create_playground_and_auth(
            client,
            xss_name,
        )

        resp = await client.get(
            f"/api/playground/{pg['share_code']}",
            cookies=cookies,
        )
        assert resp.status_code == 200
        returned_name = resp.json()["name"]
        assert "<" not in returned_name, f"Raw HTML in playground name: {returned_name}"
        assert ">" not in returned_name, f"Raw HTML in playground name: {returned_name}"


class TestCrossPlaygroundAuth:
    """BUG-003: User authed to playground A must NOT access playground B's games."""

    async def test_cannot_get_game_from_other_playground(self, client: AsyncClient):
        """User authed to playground A cannot GET a game belonging to playground B."""
        # Create two playgrounds
        pg_a, cookies_a = await _create_playground_and_auth(client, "Playground A")
        pg_b, cookies_b = await _create_playground_and_auth(client, "Playground B", pin="5678")

        # Create game in playground B
        game_b = await _create_game(client, pg_b["id"], cookies_b)

        # User A tries to access game B — should be 403
        resp = await client.get(f"/api/game/{game_b['id']}", cookies=cookies_a)
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    async def test_cannot_bid_on_other_playground_game(self, client: AsyncClient):
        """User authed to playground A cannot submit bids to playground B's game."""
        pg_a, cookies_a = await _create_playground_and_auth(client, "Bid Auth A")
        pg_b, cookies_b = await _create_playground_and_auth(client, "Bid Auth B", pin="5678")

        game_b = await _create_game(client, pg_b["id"], cookies_b)

        # User A tries to bid on game B — should be 403
        resp = await client.post(
            f"/api/game/{game_b['id']}/bid",
            json={
                "player_index": 0,
                "value": 2,
            },
            cookies=cookies_a,
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    async def test_cannot_end_other_playground_game(self, client: AsyncClient):
        """User authed to playground A cannot end playground B's game."""
        pg_a, cookies_a = await _create_playground_and_auth(client, "End Auth A")
        pg_b, cookies_b = await _create_playground_and_auth(client, "End Auth B", pin="5678")

        game_b = await _create_game(client, pg_b["id"], cookies_b)

        resp = await client.post(f"/api/game/{game_b['id']}/end", cookies=cookies_a)
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    async def test_cannot_view_scoreboard_of_other_playground(self, client: AsyncClient):
        """User authed to playground A cannot view playground B's scoreboard."""
        pg_a, cookies_a = await _create_playground_and_auth(client, "Score Auth A")
        pg_b, cookies_b = await _create_playground_and_auth(client, "Score Auth B", pin="5678")

        game_b = await _create_game(client, pg_b["id"], cookies_b)

        resp = await client.get(f"/api/game/{game_b['id']}/scoreboard", cookies=cookies_a)
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    async def test_own_playground_game_access_works(self, client: AsyncClient):
        """User authed to playground A CAN access their own games (sanity check)."""
        pg_a, cookies_a = await _create_playground_and_auth(client, "Own Auth A")

        game_a = await _create_game(client, pg_a["id"], cookies_a)

        resp = await client.get(f"/api/game/{game_a['id']}", cookies=cookies_a)
        assert resp.status_code == 200


class TestGameCreateAuth:
    """IDOR — game creation must use session playground_id, not request body."""

    async def test_cannot_create_game_under_other_playground(
        self,
        client: AsyncClient,
    ):
        """User authed to playground A must NOT create a game under playground B."""
        pg_a, cookies_a = await _create_playground_and_auth(
            client,
            "Create Auth Alpha",
        )
        pg_b, cookies_b = await _create_playground_and_auth(
            client,
            "Create Auth Beta",
            pin="5678",
        )

        # User A tries to create a game under playground B
        resp = await client.post(
            "/api/game",
            json={
                "playground_id": pg_b["id"],
                "players": ["Nadia", "Carlos", "Wei"],
                "settings": {},
            },
            cookies=cookies_a,
        )
        assert resp.status_code == 403, (
            f"Expected 403 for cross-playground game create, got {resp.status_code}"
        )

    async def test_own_playground_game_create_works(self, client: AsyncClient):
        """User authed to playground A CAN create games in their own playground."""
        pg, cookies = await _create_playground_and_auth(
            client,
            "Create Auth Own",
        )
        resp = await client.post(
            "/api/game",
            json={
                "playground_id": pg["id"],
                "players": ["Nadia", "Carlos", "Wei"],
                "settings": {},
            },
            cookies=cookies,
        )
        assert resp.status_code == 201


class TestActiveGameAuth:
    """IDOR — active game query must verify session matches path playground_id."""

    async def test_cannot_query_other_playground_active_game(
        self,
        client: AsyncClient,
    ):
        """User authed to playground A must NOT query playground B's active game."""
        pg_a, cookies_a = await _create_playground_and_auth(
            client,
            "Active Auth Alpha",
        )
        pg_b, cookies_b = await _create_playground_and_auth(
            client,
            "Active Auth Beta",
            pin="5678",
        )

        # Create a game in B
        await _create_game(client, pg_b["id"], cookies_b)

        # User A queries B's active game
        resp = await client.get(
            f"/api/game/active/{pg_b['id']}",
            cookies=cookies_a,
        )
        assert resp.status_code == 403, (
            f"Expected 403 for cross-playground active query, got {resp.status_code}"
        )

    async def test_own_playground_active_game_works(self, client: AsyncClient):
        """User can query their own playground's active game."""
        pg, cookies = await _create_playground_and_auth(
            client,
            "Active Auth Own",
        )
        await _create_game(client, pg["id"], cookies)

        resp = await client.get(
            f"/api/game/active/{pg['id']}",
            cookies=cookies,
        )
        assert resp.status_code == 200


class TestStatsEndpointAuth:
    """IDOR — stats endpoints must check playground_id matches share_code's playground."""

    async def test_cannot_read_other_playground_stats(self, client: AsyncClient):
        """User authed to playground A must NOT read playground B's stats."""
        pg_a, cookies_a = await _create_playground_and_auth(client, "Stats Crew Alpha")
        pg_b, cookies_b = await _create_playground_and_auth(client, "Stats Crew Beta")

        # Create and finish a game in playground B so it has stats
        game = await _create_game(client, pg_b["id"], cookies_b)
        await client.post(f"/api/game/{game['id']}/end", cookies=cookies_b)

        # User A tries to read B's stats
        resp = await client.get(
            f"/api/playground/{pg_b['share_code']}/stats",
            cookies=cookies_a,
        )
        assert resp.status_code == 403, (
            f"Expected 403 for cross-playground stats, got {resp.status_code}"
        )

    async def test_cannot_delete_other_playground_stats(self, client: AsyncClient):
        """User authed to playground A must NOT delete playground B's stats."""
        pg_a, cookies_a = await _create_playground_and_auth(client, "Delete Crew Alpha")
        pg_b, cookies_b = await _create_playground_and_auth(client, "Delete Crew Beta")

        game = await _create_game(client, pg_b["id"], cookies_b)
        await client.post(f"/api/game/{game['id']}/end", cookies=cookies_b)

        resp = await client.delete(
            f"/api/playground/{pg_b['share_code']}/stats",
            cookies=cookies_a,
        )
        assert resp.status_code == 403, (
            f"Expected 403 for cross-playground stats delete, got {resp.status_code}"
        )

    async def test_own_playground_stats_works(self, client: AsyncClient):
        """User authed to playground A CAN read their own stats (sanity)."""
        pg, cookies = await _create_playground_and_auth(client, "Own Stats Crew")
        game = await _create_game(client, pg["id"], cookies)
        await client.post(f"/api/game/{game['id']}/end", cookies=cookies)

        resp = await client.get(
            f"/api/playground/{pg['share_code']}/stats",
            cookies=cookies,
        )
        assert resp.status_code == 200
