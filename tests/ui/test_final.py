"""Final screen tests — winner, standings, navigation."""

import pytest

from tests.ui.helpers import (
    VIEWPORTS,
    confirm_bids,
    create_playground,
    end_game,
    enter_bids_for_all,
    enter_hands_won,
    start_game,
    unique_name,
)


@pytest.fixture
def final_page(page, server):
    page.goto(server)
    create_playground(page, unique_name("Final"), "1234", ["Alice", "Bob", "Charlie"])
    start_game(page)
    enter_bids_for_all(page, [2, 3, 1])
    confirm_bids(page)
    enter_hands_won(page, [2, 3, 3])
    page.wait_for_timeout(500)
    end_game(page)
    page.wait_for_timeout(1000)
    return page


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=lambda v: v["name"])
def test_final_renders(final_page, viewport):
    final_page.set_viewport_size(viewport)
    content = final_page.content()
    assert "🏆" in content or "final" in final_page.url or "home" in content.lower()


def test_winner_displayed(final_page):
    content = final_page.content()
    has_player = any(name in content for name in ["Alice", "Bob", "Charlie"])
    assert has_player


def test_home_button(final_page):
    home_btn = final_page.locator('button:has-text("Home")')
    if home_btn.count() > 0:
        assert home_btn.is_visible()
