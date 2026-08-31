"""Security header guard tests.

Verifies that SecurityHeadersMiddleware sets the correct headers on all responses,
HSTS is absent in debug mode and present in prod, CORS is not configured, and
session cookies carry HttpOnly + SameSite flags.
"""

import pytest

import app.main as main_module

CSP_VALUE = (
    "default-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "script-src 'self'; "
    "worker-src 'self'; "
    "img-src 'self' data:; "
    "connect-src 'self'"
)

ALWAYS_PRESENT_HEADERS = [
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "strict-origin-when-cross-origin"),
]

TEST_ROUTES = ["/api/health", "/"]


class TestAlwaysPresentHeaders:
    @pytest.mark.parametrize("header,value", ALWAYS_PRESENT_HEADERS)
    @pytest.mark.parametrize("route", TEST_ROUTES)
    async def test_header_present(self, client, header, value, route):
        response = await client.get(route)
        assert response.headers.get(header) == value, (
            f"Missing or wrong {header} on {route}: got {response.headers.get(header)!r}"
        )


class TestContentSecurityPolicy:
    async def test_csp_exact_match(self, client):
        response = await client.get("/api/health")
        assert response.headers.get("Content-Security-Policy") == CSP_VALUE

    async def test_csp_on_root(self, client):
        response = await client.get("/")
        assert response.headers.get("Content-Security-Policy") == CSP_VALUE


class TestHSTSHeader:
    async def test_hsts_absent_in_debug_mode(self, client):
        """In debug mode, HSTS must NOT be set."""
        original = main_module.settings.debug
        try:
            main_module.settings.debug = True
            response = await client.get("/api/health")
            assert "Strict-Transport-Security" not in response.headers, (
                "HSTS must not be set in debug mode"
            )
        finally:
            main_module.settings.debug = original

    async def test_hsts_present_in_prod_mode(self, client):
        """When debug=False, HSTS must be set."""
        original = main_module.settings.debug
        try:
            main_module.settings.debug = False
            response = await client.get("/api/health")
            assert "Strict-Transport-Security" in response.headers, (
                "HSTS must be present when debug=False"
            )
            hsts = response.headers["Strict-Transport-Security"]
            assert hsts == "max-age=31536000; includeSubDomains"
        finally:
            main_module.settings.debug = original


class TestCORSNotConfigured:
    async def test_no_cors_header_on_get(self, client):
        response = await client.get("/api/health")
        assert "Access-Control-Allow-Origin" not in response.headers

    async def test_no_cors_header_on_options(self, client):
        response = await client.options("/api/health")
        assert "Access-Control-Allow-Origin" not in response.headers


class TestSessionCookieFlags:
    async def test_auth_cookie_has_httponly_and_samesite(self, client):
        """POST /api/playground/auth sets a session cookie with HttpOnly + SameSite."""
        # First create a playground so auth can succeed

        # Use the API to create a playground
        create_resp = await client.post(
            "/api/playground",
            json={
                "name": "CookieTest",
                "pin": "1234",
                "players": ["A", "B"],
            },
        )
        assert create_resp.status_code in (200, 201)

        # Now authenticate
        auth_resp = await client.post(
            "/api/playground/auth",
            json={
                "name": "CookieTest",
                "pin": "1234",
            },
        )
        assert auth_resp.status_code == 200

        set_cookie = auth_resp.headers.get("set-cookie", "")
        assert set_cookie, "No Set-Cookie header on auth response"
        assert "HttpOnly" in set_cookie, f"HttpOnly missing from Set-Cookie: {set_cookie}"
        assert "SameSite" in set_cookie, f"SameSite missing from Set-Cookie: {set_cookie}"
