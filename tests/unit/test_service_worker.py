"""Service worker cache name is derived from app-shell file contents — no manual bumps."""

from pathlib import Path

import pytest

from app.services.service_worker import (
    compute_shell_cache_name,
    parse_app_shell_paths,
    render_service_worker,
    resolve_shell_file,
)

MINIMAL_SW = """\
const CACHE_NAME = '__CACHE_NAME__';
const APP_SHELL = [
    '/',
    '/static/css/style.css',
    '/static/js/app.js',
];
"""


def test_parse_app_shell_paths():
    paths = parse_app_shell_paths(MINIMAL_SW)
    assert paths == ["/", "/static/css/style.css", "/static/js/app.js"]


def test_resolve_shell_file_maps_urls(tmp_path: Path):
    static_dir = tmp_path / "static"
    assert resolve_shell_file(static_dir, "/") == static_dir / "index.html"
    assert resolve_shell_file(static_dir, "/static/js/app.js") == static_dir / "js" / "app.js"


def test_compute_shell_cache_name_changes_when_shell_file_changes(tmp_path: Path):
    static_dir = tmp_path / "static"
    (static_dir / "css").mkdir(parents=True)
    (static_dir / "js").mkdir(parents=True)
    (static_dir / "index.html").write_text("home-v1", encoding="utf-8")
    (static_dir / "css" / "style.css").write_text("css-v1", encoding="utf-8")
    (static_dir / "js" / "app.js").write_text("js-v1", encoding="utf-8")
    (static_dir / "sw.js").write_text(MINIMAL_SW, encoding="utf-8")

    first = compute_shell_cache_name(static_dir, MINIMAL_SW)
    assert first.startswith("scokeep-")
    assert len(first) == len("scokeep-") + 12

    (static_dir / "js" / "app.js").write_text("js-v2-changed", encoding="utf-8")
    second = compute_shell_cache_name(static_dir, MINIMAL_SW)
    assert second != first


def test_render_service_worker_injects_cache_name(tmp_path: Path):
    static_dir = tmp_path / "static"
    (static_dir / "css").mkdir(parents=True)
    (static_dir / "js").mkdir(parents=True)
    (static_dir / "index.html").write_text("home", encoding="utf-8")
    (static_dir / "css" / "style.css").write_text("css", encoding="utf-8")
    (static_dir / "js" / "app.js").write_text("js", encoding="utf-8")
    (static_dir / "sw.js").write_text(MINIMAL_SW, encoding="utf-8")

    rendered = render_service_worker(static_dir)
    assert "__CACHE_NAME__" not in rendered
    assert "const CACHE_NAME = 'scokeep-" in rendered
    expected = compute_shell_cache_name(static_dir, MINIMAL_SW)
    assert f"const CACHE_NAME = '{expected}'" in rendered


@pytest.mark.asyncio
async def test_sw_route_is_content_hashed_and_not_long_cached(client):
    response = await client.get("/sw.js")
    assert response.status_code == 200
    cache_control = response.headers.get("cache-control", "").lower()
    assert "no-cache" in cache_control or "max-age=0" in cache_control
    assert "scokeep-" in response.text
    assert "__CACHE_NAME__" not in response.text
    assert "APP_SHELL" in response.text


def test__service_worker_response_sets_no_cache_headers():
    from app.main import _service_worker_response

    response = _service_worker_response()
    assert "no-cache" in response.headers["Cache-Control"]
    assert response.headers.get("Service-Worker-Allowed") == "/"
    assert b"__CACHE_NAME__" not in response.body
    assert b"scokeep-" in response.body


@pytest.mark.asyncio
async def test_sw_register_auto_versions_from_sw_body(client):
    register = await client.get("/static/js/sw-register.js")
    index = await client.get("/")
    assert register.status_code == 200
    assert index.status_code == 200
    # No hard-coded scokeep-vNN — register derives version from /sw.js at runtime
    assert "scokeep-v82" not in register.text
    assert "/sw.js" in register.text
    assert "cache: 'no-store'" in register.text or 'cache: "no-store"' in register.text
    assert "sw-register.js?v=" not in index.text
    assert 'src="/static/js/sw-register.js"' in index.text
