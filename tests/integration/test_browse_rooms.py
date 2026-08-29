"""Browse Rooms tests — public endpoint to list all room names alphabetically."""

from httpx import AsyncClient


async def _create_playground(client: AsyncClient, name: str):
    await client.post(
        "/api/playground",
        json={"name": name, "pin": "1234", "players": ["Alice", "Bob"]},
    )


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

    async def test_browse_returns_name_and_share_code_only(self, client: AsyncClient):
        """Response must have name + share_code, no players/pin_hash/insights."""
        await _create_playground(client, "Test Room")

        resp = await client.get("/api/playground/browse")
        room = resp.json()["rooms"][0]
        assert "name" in room
        assert "share_code" in room
        assert "pin_hash" not in room
        assert "players" not in room
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
