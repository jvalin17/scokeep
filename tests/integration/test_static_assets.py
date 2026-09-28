"""Integration tests for static assets and browser-requested resources.

Verifies that all files the browser auto-requests (favicon, icons,
manifest, service worker) and all JS modules are served correctly.
"""

from httpx import AsyncClient


class TestBrowserAssets:
    """Files browsers request automatically — must not 404."""

    async def test_favicon(self, client: AsyncClient):
        response = await client.get("/favicon.ico")
        assert response.status_code == 200

    async def test_apple_touch_icon(self, client: AsyncClient):
        response = await client.get("/apple-touch-icon.png")
        assert response.status_code == 200

    async def test_apple_touch_icon_precomposed(self, client: AsyncClient):
        response = await client.get("/apple-touch-icon-precomposed.png")
        assert response.status_code == 200


class TestPWAAssets:
    """PWA manifest, service worker, and icons."""

    async def test_manifest(self, client: AsyncClient):
        response = await client.get("/static/manifest.json")
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Scokeep"
        assert body["display"] == "standalone"
        assert len(body["icons"]) >= 2

    async def test_service_worker(self, client: AsyncClient):
        response = await client.get("/sw.js")
        assert response.status_code == 200
        assert "CACHE_NAME" in response.text
        assert "__CACHE_NAME__" not in response.text
        assert "scokeep-" in response.text

    async def test_service_worker_is_not_long_cached(self, client: AsyncClient):
        """SW must revalidate — a long-lived CDN cache freezes the old app shell."""
        import app.main as main_module

        original = main_module.settings.debug
        try:
            main_module.settings.debug = False
            response = await client.get("/sw.js")
        finally:
            main_module.settings.debug = original
        assert response.status_code == 200
        cache_control = response.headers.get("cache-control", "").lower()
        assert "no-cache" in cache_control or "max-age=0" in cache_control, (
            f"sw.js must not be long-cached; got Cache-Control={cache_control!r}"
        )

    async def test_service_worker_static_alias_matches(self, client: AsyncClient):
        primary = await client.get("/sw.js")
        alias = await client.get("/static/sw.js")
        assert primary.status_code == 200 and alias.status_code == 200
        assert primary.text == alias.text

    async def test_icon_192(self, client: AsyncClient):
        response = await client.get("/static/icons/icon-192.png")
        assert response.status_code == 200

    async def test_icon_512(self, client: AsyncClient):
        response = await client.get("/static/icons/icon-512.png")
        assert response.status_code == 200


class TestJSModules:
    """Every JS module must be loadable — missing modules break the app."""

    JS_FILES = [
        "/static/js/app.js",
        "/static/js/api.js",
        "/static/js/screens/home.js",
        "/static/js/screens/lobby.js",
        "/static/js/screens/bidding.js",
        "/static/js/screens/play.js",
        "/static/js/screens/roundend.js",
        "/static/js/screens/scoreboard.js",
        "/static/js/screens/final.js",
        "/static/js/screens/stats.js",
        "/static/js/components/keypad.js",
        "/static/js/components/sounds.js",
        "/static/js/components/logger.js",
        "/static/js/components/game-utils.js",
        "/static/js/components/drag-reorder.js",
    ]

    async def test_all_js_modules_serve_200(self, client: AsyncClient):
        for path in self.JS_FILES:
            response = await client.get(path)
            assert response.status_code == 200, f"{path} returned {response.status_code}"

    async def test_css_serves(self, client: AsyncClient):
        response = await client.get("/static/css/style.css")
        assert response.status_code == 200

    async def test_index_html(self, client: AsyncClient):
        response = await client.get("/")
        assert response.status_code == 200
        assert "Scokeep" in response.text


class TestHealthEndpoint:
    async def test_health_returns_status(self, client: AsyncClient):
        from unittest.mock import patch

        from tests.conftest import test_engine

        with patch("app.main.engine", test_engine):
            response = await client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] in ("healthy", "unhealthy")
