"""Integration test for BUG-005: rate limiting on auth endpoints.

AUTH_RATE_LIMIT = "5/minute" — the 6th request within a minute must return 429.

conftest.py sets RATE_LIMIT_ENABLED=false globally so existing tests are
unaffected.  This module re-enables the limiter for each test by patching
app.config.settings.rate_limit_enabled and rebuilding the limiter's enabled
state on the Slowapi Limiter instance directly.

Strategy:
  - The `Limiter` object on playground.limiter stores `_enabled`.
  - We temporarily set it to True inside the test, then restore it on teardown.
  - We also need each request to look like it comes from the same IP address
    so the per-key counter accumulates — ASGI tests default to 127.0.0.1
    which is what get_remote_address returns.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.routes.playground import limiter


async def _create_playground(client: AsyncClient, name: str) -> dict:
    resp = await client.post(
        "/api/playground",
        json={
            "name": name,
            "pin": "7890",
            "players": ["Kavya", "Suresh", "Lalitha"],
        },
    )
    assert resp.status_code == 201, f"Setup failed: {resp.text}"
    return resp.json()


class TestBug005AuthRateLimiting:
    """Rate limiter must reject the 6th auth attempt within a minute with 429."""

    @pytest.fixture(autouse=True)
    def enable_rate_limiter(self):
        """Temporarily enable the rate limiter for tests in this class."""
        original = limiter.enabled
        limiter.enabled = True
        limiter.reset()
        yield
        limiter.enabled = original

    @pytest.fixture
    async def rate_limit_client(self) -> AsyncClient:
        """Client with a deterministic remote address for consistent key bucketing.

        slowapi's get_remote_address reads the 'x-forwarded-for' header or the
        client host.  Using ASGITransport the host is 127.0.0.1 by default.
        """
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as c:
            yield c

    async def test_auth_endpoint_blocks_on_sixth_request(self, rate_limit_client):
        """POST /api/playground/auth must 429 on the 6th call within the window."""
        client = rate_limit_client
        await _create_playground(client, "Rate Limit Auth Test")

        # 5 requests should all succeed (wrong PIN → 401 but not 429)
        for attempt in range(1, 6):
            resp = await client.post(
                "/api/playground/auth",
                json={"name": "Rate Limit Auth Test", "pin": "9999"},
            )
            assert resp.status_code != 429, (
                f"Request #{attempt} should not be rate-limited yet, got 429"
            )

        # 6th request must be blocked
        resp = await client.post(
            "/api/playground/auth",
            json={"name": "Rate Limit Auth Test", "pin": "9999"},
        )
        assert resp.status_code == 429, (
            f"6th auth request must return 429 (rate limited), got {resp.status_code}"
        )

    async def test_pin_hint_endpoint_blocks_on_sixth_request(self, rate_limit_client):
        """GET /api/playground/hint/{name} also carries AUTH_RATE_LIMIT.
        The 6th call must return 429."""
        client = rate_limit_client
        await _create_playground(client, "Rate Limit Hint Test")

        for attempt in range(1, 6):
            resp = await client.get("/api/playground/hint/Rate Limit Hint Test")
            assert resp.status_code != 429, (
                f"Request #{attempt} should not be rate-limited yet, got 429"
            )

        resp = await client.get("/api/playground/hint/Rate Limit Hint Test")
        assert resp.status_code == 429, (
            f"6th hint request must return 429 (rate limited), got {resp.status_code}"
        )

    async def test_correct_auth_still_works_within_limit(self, rate_limit_client):
        """Successful auth must work on the first 5 attempts; only the 6th is blocked."""
        client = rate_limit_client
        await _create_playground(client, "Rate Limit Success Test")

        # 5 correct auths should all return 200
        for attempt in range(1, 6):
            resp = await client.post(
                "/api/playground/auth",
                json={"name": "Rate Limit Success Test", "pin": "7890"},
            )
            assert resp.status_code == 200, (
                f"Correct auth #{attempt} must succeed (200), got {resp.status_code}"
            )

        # 6th — rate limited regardless of whether PIN is correct
        resp = await client.post(
            "/api/playground/auth",
            json={"name": "Rate Limit Success Test", "pin": "7890"},
        )
        assert resp.status_code == 429, (
            f"6th auth must be rate-limited (429) even with correct PIN, got {resp.status_code}"
        )
