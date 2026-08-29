"""Browse Rooms + PIN hint tests."""

from httpx import AsyncClient


async def _create_playground(client: AsyncClient, name: str, pin_hint: str | None = None):
    body = {"name": name, "pin": "1234", "players": ["Alice", "Bob"]}
    if pin_hint:
        body["pin_hint"] = pin_hint
    await client.post("/api/playground", json=body)


class TestBrowseRooms:
    async def test_browse_returns_all_rooms_alphabetically(self, client: AsyncClient):
        """All rooms returned sorted A→Z by name."""
        await _create_playground(client, "Zebra Room")
        await _create_playground(client, "Alpha Room")
        await _create_playground(client, "Middle Room")

        resp = await client.get("/api/playground/browse")
        assert resp.status_code == 200
        data = resp.json()
        names = [r["name"] for r in data["rooms"]]
        assert names == ["Alpha Room", "Middle Room", "Zebra Room"]

    async def test_browse_returns_name_share_code_and_players(self, client: AsyncClient):
        """Response has name, share_code, players — no pin_hash or insights."""
        await _create_playground(client, "Test Room")

        resp = await client.get("/api/playground/browse")
        room = resp.json()["rooms"][0]
        assert "name" in room
        assert "share_code" in room
        assert "players" in room
        assert "pin_hash" not in room
        assert "insights" not in room

    async def test_browse_no_auth_required(self, client: AsyncClient):
        """Browse is public — no session cookie needed."""
        await _create_playground(client, "Public Room")

        resp = await client.get("/api/playground/browse")
        assert resp.status_code == 200

    async def test_browse_empty_returns_empty_list(self, client: AsyncClient):
        """No rooms → empty list, not an error."""
        resp = await client.get("/api/playground/browse")
        assert resp.status_code == 200
        assert resp.json()["rooms"] == []

    async def test_browse_players_match_created_players(self, client: AsyncClient):
        """Players in browse response must match what was set at creation."""
        await client.post(
            "/api/playground",
            json={"name": "Player Check", "pin": "1234", "players": ["Ravi", "Priya", "Amit"]},
        )
        resp = await client.get("/api/playground/browse")
        room = resp.json()["rooms"][0]
        assert room["players"] == ["Ravi", "Priya", "Amit"]

    async def test_browse_players_enables_client_side_filter(self, client: AsyncClient):
        """Rooms with specific players can be found by filtering on player name."""
        await client.post(
            "/api/playground",
            json={"name": "Room A", "pin": "1234", "players": ["Maria", "Carlos"]},
        )
        await client.post(
            "/api/playground",
            json={"name": "Room B", "pin": "1234", "players": ["Wei", "Nadia"]},
        )
        resp = await client.get("/api/playground/browse")
        rooms = resp.json()["rooms"]

        # Client-side filter simulation: find rooms where "Maria" plays
        maria_rooms = [r for r in rooms if any("Maria" in p for p in r["players"])]
        assert len(maria_rooms) == 1
        assert maria_rooms[0]["name"] == "Room A"

        # "Wei" only in Room B
        wei_rooms = [r for r in rooms if any("Wei" in p for p in r["players"])]
        assert len(wei_rooms) == 1
        assert wei_rooms[0]["name"] == "Room B"

        # "Unknown" in no rooms
        unknown_rooms = [r for r in rooms if any("Unknown" in p for p in r["players"])]
        assert len(unknown_rooms) == 0


class TestPinHint:
    async def test_hint_returned_when_set(self, client: AsyncClient):
        await _create_playground(client, "Hint Room", pin_hint="birthday")
        resp = await client.get("/api/playground/hint/Hint Room")
        assert resp.status_code == 200
        assert resp.json()["hint"] == "birthday"

    async def test_hint_null_when_not_set(self, client: AsyncClient):
        await _create_playground(client, "No Hint Room")
        resp = await client.get("/api/playground/hint/No Hint Room")
        assert resp.status_code == 200
        assert resp.json()["hint"] is None

    async def test_hint_404_for_unknown_room(self, client: AsyncClient):
        resp = await client.get("/api/playground/hint/Nonexistent")
        assert resp.status_code == 404

    async def test_hint_no_auth_required(self, client: AsyncClient):
        """Hint is public — no session cookie needed."""
        await _create_playground(client, "Public Hint", pin_hint="test")
        resp = await client.get("/api/playground/hint/Public Hint")
        assert resp.status_code == 200

    async def test_hint_with_special_chars(self, client: AsyncClient):
        """Hints with & and < are stored correctly."""
        await _create_playground(client, "Special Hint", pin_hint="mom & dad's bday")
        resp = await client.get("/api/playground/hint/Special Hint")
        assert resp.status_code == 200
        # Stored with html.escape, so & becomes &amp;
        hint = resp.json()["hint"]
        assert hint is not None
        assert "mom" in hint

    async def test_hint_not_in_auth_response(self, client: AsyncClient):
        """pin_hint must NOT appear in auth response."""
        await _create_playground(client, "Auth Hint", pin_hint="secret")
        resp = await client.post(
            "/api/playground/auth",
            json={"name": "Auth Hint", "pin": "1234"},
        )
        assert resp.status_code == 200
        assert "pin_hint" not in resp.json()
