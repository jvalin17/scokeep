"""Lobby screen tests — player list, settings, start game."""

import pytest

from tests.ui.helpers import VIEWPORTS, create_playground, unique_name


@pytest.fixture
def lobby_page(page, server):
    page.goto(server)
    create_playground(page, unique_name("Lobby"), "1234", ["Alice", "Bob", "Charlie"])
    return page


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=lambda v: v["name"])
def test_lobby_renders(lobby_page, viewport):
    """Lobby renders at all viewports."""
    lobby_page.set_viewport_size(viewport)
    lobby_page.wait_for_selector(".lobby-player", timeout=5000)
    content = lobby_page.content()
    has_players = any(name in content for name in ["Alice", "Bob", "Charlie"])
    assert has_players


def test_start_game_button_visible(lobby_page):
    """Start Game button is present."""
    btn = lobby_page.locator('button:has-text("Start Game")')
    btn.wait_for(state="visible", timeout=10000)
    assert btn.is_visible()


def test_settings_section_exists(lobby_page):
    """Game settings (mode, appearance) are visible."""
    content = lobby_page.content()
    has_settings = (
        "expert" in content.lower() or "rookie" in content.lower() or "friendly" in content.lower()
    )
    assert has_settings


def test_player_list_shows_all(lobby_page):
    """All added players appear in the lobby."""
    lobby_page.wait_for_selector(".lobby-player", timeout=5000)
    content = lobby_page.content()
    for name in ["Alice", "Bob", "Charlie"]:
        assert name in content


def test_no_horizontal_overflow(lobby_page):
    """No horizontal scroll on lobby."""
    overflow = lobby_page.evaluate(
        "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )
    assert not overflow


def test_sound_mute_toggle(lobby_page):
    """Toggle-sound button switches between 🔊 and 🔇 and persists to localStorage."""
    page = lobby_page
    toggle = page.locator("#toggle-sound")
    toggle.wait_for(state="visible", timeout=10000)
    initial_text = toggle.inner_text()
    assert "🔊" in initial_text, f"Expected 🔊 initially, got: {initial_text!r}"
    toggle.click()
    page.wait_for_function(
        "() => document.querySelector('#toggle-sound')?.innerText?.includes('🔇')",
        timeout=3000,
    )
    muted_text = toggle.inner_text()
    assert "🔇" in muted_text, f"Expected 🔇 after click, got: {muted_text!r}"
    stored = page.evaluate("() => localStorage.getItem('scokeep_mute')")
    assert stored == "1", f"Expected localStorage scokeep_mute='1', got: {stored!r}"


def test_lobby_add_player(lobby_page):
    """Typing a name and clicking Add appends that player to the list."""
    page = lobby_page
    page.wait_for_selector("#add-player-btn", timeout=5000)
    before = page.locator(".lobby-player").count()
    page.fill("#new-player", "Diana")
    page.click("#add-player-btn")
    page.wait_for_function(
        f"() => document.querySelectorAll('.lobby-player').length === {before + 1}",
        timeout=3000,
    )
    assert "Diana" in page.locator("#player-list").inner_text()


def test_lobby_add_player_shows_error_at_max(page, server):
    """At 8 players, Add must show an error instead of silently doing nothing."""
    page.goto(server)
    eight = [f"P{i}" for i in range(1, 9)]
    create_playground(page, unique_name("Full"), "1234", eight)
    page.wait_for_selector("#add-player-btn", timeout=5000)
    assert page.locator(".lobby-player").count() == 8
    page.fill("#new-player", "Ninth")
    page.click("#add-player-btn")
    err = page.locator("#lobby-error")
    err.wait_for(state="visible", timeout=3000)
    assert "8" in err.inner_text()
    assert page.locator(".lobby-player").count() == 8
