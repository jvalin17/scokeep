"""Integration tests for playground API endpoints.

Tests the full HTTP request/response cycle including validation,
PIN hashing, cookie-based auth, and error handling.
"""

from httpx import AsyncClient


class TestCreatePlayground:

    async def test_create_returns_share_code(self, client: AsyncClient):
        response = await client.post("/api/playground", json={
            "name": "The Jokers",
            "pin": "1234",
            "players": ["Alice", "Bob", "Charlie"],
        })

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "The Jokers"
        assert len(body["share_code"]) == 4
        assert body["players"] == ["Alice", "Bob", "Charlie"]
        assert "pin" not in body
        assert "pin_hash" not in body

    async def test_create_missing_name_returns_422(self, client: AsyncClient):
        response = await client.post("/api/playground", json={
            "pin": "1234",
            "players": ["Alice"],
        })

        assert response.status_code == 422

    async def test_create_empty_players_returns_422(self, client: AsyncClient):
        response = await client.post("/api/playground", json={
            "name": "Test",
            "pin": "1234",
            "players": [],
        })

        assert response.status_code == 422


class TestAuthPlayground:

    async def test_auth_correct_pin_returns_playground(self, client: AsyncClient):
        await client.post("/api/playground", json={
            "name": "Auth Test",
            "pin": "5678",
            "players": ["A"],
        })

        response = await client.post("/api/playground/auth", json={
            "name": "Auth Test",
            "pin": "5678",
        })

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Auth Test"
        assert len(body["share_code"]) == 4
        assert "scokeep_session" in response.cookies

    async def test_auth_wrong_pin_returns_401(self, client: AsyncClient):
        await client.post("/api/playground", json={
            "name": "Auth Test 2",
            "pin": "5678",
            "players": ["A"],
        })

        response = await client.post("/api/playground/auth", json={
            "name": "Auth Test 2",
            "pin": "0000",
        })

        assert response.status_code == 401

    async def test_auth_nonexistent_playground_returns_404(self, client: AsyncClient):
        response = await client.post("/api/playground/auth", json={
            "name": "Does Not Exist",
            "pin": "1234",
        })

        assert response.status_code == 404


class TestGetPlayground:

    async def test_get_with_valid_session_returns_playground(self, client: AsyncClient):
        create_response = await client.post("/api/playground", json={
            "name": "Get Test",
            "pin": "1234",
            "players": ["X", "Y", "Z"],
        })
        share_code = create_response.json()["share_code"]

        # Authenticate first
        auth_response = await client.post("/api/playground/auth", json={
            "name": "Get Test",
            "pin": "1234",
        })
        session_cookie = auth_response.cookies.get("scokeep_session")

        # Get playground with session cookie
        response = await client.get(
            f"/api/playground/{share_code}",
            cookies={"scokeep_session": session_cookie},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Get Test"
        assert body["players"] == ["X", "Y", "Z"]

    async def test_get_without_session_returns_401(self, client: AsyncClient):
        create_response = await client.post("/api/playground", json={
            "name": "No Auth Test",
            "pin": "1234",
            "players": ["A"],
        })
        share_code = create_response.json()["share_code"]

        response = await client.get(f"/api/playground/{share_code}")

        assert response.status_code == 401

    async def test_get_nonexistent_code_returns_404(self, client: AsyncClient):
        # Auth to some playground first
        await client.post("/api/playground", json={
            "name": "Exists",
            "pin": "1234",
            "players": ["A"],
        })
        auth_response = await client.post("/api/playground/auth", json={
            "name": "Exists",
            "pin": "1234",
        })
        session_cookie = auth_response.cookies.get("scokeep_session")

        response = await client.get(
            "/api/playground/ZZZZZZZZ",
            cookies={"scokeep_session": session_cookie},
        )

        assert response.status_code == 404


class TestDeletePlayground:

    async def test_delete_with_correct_pin(self, client: AsyncClient):
        """Delete playground with correct PIN removes it and all data."""
        await client.post("/api/playground", json={
            "name": "Delete Me", "pin": "4321",
            "players": ["Nadia", "Carlos"],
        })
        # Create a game in it
        auth = await client.post("/api/playground/auth", json={
            "name": "Delete Me", "pin": "4321",
        })
        cookies = {"scokeep_session": auth.cookies.get("scokeep_session")}
        await client.post("/api/game", json={
            "playground_id": auth.json()["id"],
            "players": ["Nadia", "Carlos"],
            "settings": {},
        }, cookies=cookies)

        # Delete
        resp = await client.request(
            "DELETE", "/api/playground",
            json={"name": "Delete Me", "pin": "4321"},
        )
        assert resp.status_code == 200
        assert resp.json()["deleted"] == "Delete Me"

        # Verify it's gone
        auth2 = await client.post("/api/playground/auth", json={
            "name": "Delete Me", "pin": "4321",
        })
        assert auth2.status_code == 404

    async def test_delete_with_wrong_pin_returns_401(self, client: AsyncClient):
        """Cannot delete playground with wrong PIN."""
        await client.post("/api/playground", json={
            "name": "Protected Room", "pin": "9999",
            "players": ["Wei", "Priya"],
        })

        resp = await client.request(
            "DELETE", "/api/playground",
            json={"name": "Protected Room", "pin": "0000"},
        )
        assert resp.status_code == 401

    async def test_delete_nonexistent_returns_404(self, client: AsyncClient):
        """Cannot delete playground that doesn't exist."""
        resp = await client.request(
            "DELETE", "/api/playground",
            json={"name": "Ghost Room", "pin": "1234"},
        )
        assert resp.status_code == 404
