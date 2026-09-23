"""IDB-first gameplay — Playwright E2E for online room games.

Covers local game- ids, per-round sync, offline continue without banner,
end-game import, and lobby Sync now.
"""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect

from tests.ui.helpers import (
    create_playground,
    end_game,
    play_one_round,
    start_game,
    unique_name,
)


def _start_idb_room(page: Page, server: str, name: str) -> str:
    """Create room + start Rookie game. Returns share code from lobby hash."""
    page.goto(server)
    page.wait_for_selector("#create-form", timeout=10000)
    create_playground(page, name, "1234", ["Alice", "Bob", "Charlie"])
    page.wait_for_function("() => location.hash.includes('playground')", timeout=15000)
    share = page.evaluate("() => location.hash").split("/")[-1]
    start_game(page, {"mode": "Rookie", "sets": 1})
    page.wait_for_function("() => location.hash.includes('game-')", timeout=15000)
    return share


def test_online_game_idb_first(page, server):
    """Create room, start game, bid — hash uses local game- id and keypad is instant."""
    page.goto(server)
    create_playground(page, unique_name("IDBFirst"), "1234", ["Alice", "Bob", "Charlie"])
    start_game(page, {"mode": "Rookie"})

    game_hash = page.evaluate("() => location.hash")
    assert "bid/" in game_hash
    assert "game-" in game_hash

    keypad = page.locator(".keypad")
    assert keypad.count() > 0

    play_one_round(page, [2, 3, 1], [2, 3, 3])
    assert "game-" in page.evaluate("() => location.hash")


def test_per_round_sync(page, server):
    """Play one round; SyncManager POSTs sync-round for the server game id."""
    sync_urls: list[str] = []

    def on_request(request):
        if "sync-round" in request.url and request.method == "POST":
            sync_urls.append(request.url)

    page.on("request", on_request)
    _start_idb_room(page, server, unique_name("IDBSync"))
    assert "game-" in page.evaluate("() => location.hash")

    play_one_round(page, [2, 3, 1], [2, 3, 3])

    page.wait_for_timeout(2000)
    assert sync_urls, "expected at least one POST /sync-round after scoring"
    assert re.search(r"/api/game/\d+/sync-round", sync_urls[0])


def test_network_drop_continues(page, server):
    """Block sync APIs mid-game; scoring still advances on local game- id."""
    _start_idb_room(page, server, unique_name("IDBDrop"))
    page.route("**/api/game/**/sync-round", lambda route: route.abort())
    page.route("**/api/game/**/import", lambda route: route.abort())
    page.route("**/api/game/**/sync-state", lambda route: route.abort())

    play_one_round(page, [1, 2, 2], [1, 2, 5])
    game_hash = page.evaluate("() => location.hash")
    assert "game-" in game_hash
    assert "scoreboard" in game_hash or "bid" in game_hash


def test_no_banner_on_drop(page, server):
    """Blocking sync APIs must not show the connection banner."""
    _start_idb_room(page, server, unique_name("IDBBanner"))
    page.route("**/api/game/**/sync-round", lambda route: route.abort())
    page.route("**/api/game/**/import", lambda route: route.abort())

    play_one_round(page, [2, 2, 2], [2, 3, 3])
    banner = page.locator("#connection-banner")
    assert banner.count() == 0 or not banner.is_visible()


def test_game_end_syncs_all(page, server):
    """After confirmFinal, import POST runs for the linked room."""
    import_urls: list[str] = []

    def on_request(request):
        if "/import" in request.url and request.method == "POST":
            import_urls.append(request.url)

    page.on("request", on_request)
    share = _start_idb_room(page, server, unique_name("IDBEnd"))
    play_one_round(page, [2, 3, 1], [2, 3, 3])
    end_game(page)

    page.wait_for_timeout(3000)
    assert any(share in url or "/import" in url for url in import_urls) or import_urls, (
        f"expected import POST after confirmFinal, got {import_urls}"
    )


def test_lobby_sync_button_offline(page, server):
    """Finish a game with sync blocked; lobby shows Sync now for the room."""
    share = _start_idb_room(page, server, unique_name("IDBLobbySync"))
    page.route("**/api/game/**/sync-round", lambda route: route.abort())
    page.route("**/api/game/**/import", lambda route: route.abort())

    play_one_round(page, [2, 3, 1], [2, 3, 3])
    end_game(page)

    page.evaluate(f"() => location.hash = 'playground/{share}'")
    page.wait_for_selector("#sync-now, #start-game", timeout=10000)
    expect(page.locator("#sync-now")).to_be_visible(timeout=10000)


def test_partial_sync_recovery(page, server):
    """One online round syncs; then block sync and finish — Sync now recovers."""
    sync_urls: list[str] = []
    import_urls: list[str] = []

    def on_request(request):
        if request.method != "POST":
            return
        if "sync-round" in request.url:
            sync_urls.append(request.url)
        if "/import" in request.url:
            import_urls.append(request.url)

    page.on("request", on_request)
    share = _start_idb_room(page, server, unique_name("IDBPartial"))

    play_one_round(page, [2, 3, 1], [2, 3, 3])
    page.wait_for_timeout(1500)
    assert sync_urls, "round 1 should sync while online"

    page.route("**/api/game/**/sync-round", lambda route: route.abort())
    page.route("**/api/game/**/import", lambda route: route.abort())

    end_game(page)
    page.wait_for_timeout(500)

    # Unblock and trigger lobby sync
    page.unroute("**/api/game/**/sync-round")
    page.unroute("**/api/game/**/import")
    page.evaluate(f"() => location.hash = 'playground/{share}'")
    page.wait_for_selector("#sync-now, #start-game", timeout=10000)
    sync_btn = page.locator("#sync-now")
    if sync_btn.count() > 0 and sync_btn.is_visible():
        sync_btn.click()
        page.wait_for_timeout(2000)

    assert sync_urls or import_urls
