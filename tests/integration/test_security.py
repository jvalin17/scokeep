"""Security tests — XSS prevention and cross-playground authorization.

BUG-002: XSS via player names — names must be HTML-escaped server-side
BUG-003: Cross-playground auth — user authed to playground A must NOT access games in playground B
"""

from httpx import AsyncClient


async def _create_playground_and_auth(
    client: AsyncClient, name: str, pin: str = "1234", players: list[str] | None = None,
):
    """Create playground, auth, return (playground_dict, cookies)."""
    players = players or ["Alice", "Bob", "Charlie"]
    await client.post("/api/playground", json={
        "name": name, "pin": pin, "players": players,
    })
    auth = await client.post("/api/playground/auth", json={
        "name": name, "pin": pin,
    })
    cookies = {"scokeep_session": auth.cookies.get("scokeep_session")}
    return auth.json(), cookies


async def _create_game(
    client: AsyncClient, playground_id: int, cookies: dict,
    players: list[str] | None = None,
):
    """Create a game and return the game dict."""
    players = players or ["Alice", "Bob", "Charlie"]
    resp = await client.post("/api/game", json={
        "playground_id": playground_id,
        "players": players,
        "settings": {"num_sets": 1},
    }, cookies=cookies)
    return resp.json()


class TestXSSPrevention:
    """BUG-002: Player names with HTML/script must be escaped in API responses."""

    async def test_html_in_player_name_is_escaped_in_response(self, client: AsyncClient):
        """API should escape player names containing HTML tags."""
        xss_name = '<img onerror=alert(1) src=x>'
        pg, cookies = await _create_playground_and_auth(
            client, "XSS Test", players=[xss_name, "Bob", "Charlie"],
        )

        # The stored name should be sanitized
        resp = await client.get(
            f"/api/playground/{pg['share_code']}", cookies=cookies,
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
            client, "XSS Script Test", players=[xss_name, "Bob"],
        )

        game = await _create_game(client, pg["id"], cookies, players=[xss_name, "Bob"])
        # Player names in game response must be clean
        for name in game["players"]:
            assert "<script>" not in name, f"Script tag in player name: {name}"


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
        resp = await client.post(f"/api/game/{game_b['id']}/bid", json={
            "player_index": 0, "value": 2,
        }, cookies=cookies_a)
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
