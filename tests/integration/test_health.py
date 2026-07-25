from httpx import AsyncClient


async def test_health_endpoint_returns_healthy(client: AsyncClient):
    response = await client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["database"] == "connected"


async def test_index_returns_html(client: AsyncClient):
    response = await client.get("/")

    assert response.status_code == 200
    assert "Scokeep" in response.text
