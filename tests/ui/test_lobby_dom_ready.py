"""Regression test: lobby content must be checked after DOM is ready.

Bug: test_lobby_renders and test_player_list_shows_all called page.content()
immediately after set_viewport_size(), getting raw HTML instead of rendered SPA.
Under CI load, the SPA hadn't re-rendered yet.

This test verifies that player names are present in the DOM after waiting for
the .lobby-player selector — not just checking raw HTML.
"""

import pytest

from tests.ui.helpers import VIEWPORTS, create_playground, unique_name


@pytest.fixture
def lobby_page(page, server):
    page.goto(server)
    create_playground(page, unique_name("DOMReady"), "1234", ["Alice", "Bob", "Charlie"])
    return page


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=lambda v: v["name"])
def test_lobby_content_after_dom_ready(lobby_page, viewport):
    """After viewport change, wait for DOM before checking content."""
    lobby_page.set_viewport_size(viewport)
    # Must wait for SPA to render — raw HTML check is flaky
    lobby_page.wait_for_selector(".lobby-player", timeout=5000)
    content = lobby_page.content()
    has_players = any(name in content for name in ["Alice", "Bob", "Charlie"])
    assert has_players, "Player names not found in DOM after waiting for .lobby-player"
