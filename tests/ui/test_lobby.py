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
    content = lobby_page.content()
    has_players = any(name in content for name in ["Alice", "Bob", "Charlie"])
    assert has_players


def test_start_game_button_visible(lobby_page):
    """Start Game button is present."""
    btn = lobby_page.locator('button:has-text("Start Game")')
    assert btn.count() > 0
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
    content = lobby_page.content()
    for name in ["Alice", "Bob", "Charlie"]:
        assert name in content


def test_no_horizontal_overflow(lobby_page):
    """No horizontal scroll on lobby."""
    overflow = lobby_page.evaluate(
        "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )
    assert not overflow
