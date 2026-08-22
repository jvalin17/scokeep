from unittest.mock import AsyncMock, patch

from httpx import AsyncClient


async def test_health_endpoint_returns_healthy(client: AsyncClient):
    response = await client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["database"] == "connected"


async def test_health_returns_503_on_db_failure(client: AsyncClient):
    """Health check must return 503 when the database is unreachable."""
    with patch("app.main.engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(side_effect=ConnectionError("DB down"))
        mock_engine.begin.return_value = mock_conn

        response = await client.get("/api/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unhealthy"
    assert body["database"] == "unavailable"


async def test_index_returns_html(client: AsyncClient):
    response = await client.get("/")

    assert response.status_code == 200
    assert "Scokeep" in response.text
