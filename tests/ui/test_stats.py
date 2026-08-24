"""Stats screen tests — tabs, scoresheet expand, chart, insights."""

import pytest

from tests.ui.helpers import (
    VIEWPORTS,
    confirm_bids,
    create_playground,
    end_game,
    enter_bids_for_all,
    enter_hands_won,
    navigate_to_stats,
    start_game,
    unique_name,
)


@pytest.fixture
def stats_page(page, server):
    name = unique_name("Stats")
    page.goto(server)
    create_playground(page, name, "1234", ["Alice", "Bob", "Charlie"])
    start_game(page)
    enter_bids_for_all(page, [2, 3, 1])
    confirm_bids(page)
    enter_hands_won(page, [2, 3, 3])
    # Score the round before ending the game
    score_btn = page.locator('button:has-text("Score Round")')
    if score_btn.count() > 0:
        score_btn.click()
        page.wait_for_timeout(1000)
    end_game(page)
    page.wait_for_timeout(500)

    navigate_to_stats(page, server, name, "1234")
    return page


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=lambda v: v["name"])
def test_stats_renders(stats_page, viewport):
    stats_page.set_viewport_size(viewport)
    tabs = stats_page.locator(".stats-tab")
    assert tabs.count() >= 2, "Stats tabs not rendered"


def test_tabs_exist(stats_page):
    tabs = stats_page.locator(".stats-tab")
    assert tabs.count() >= 2


def test_tab_switching(stats_page):
    tabs = stats_page.locator(".stats-tab")
    if tabs.count() >= 2:
        tabs.nth(1).click()
        stats_page.wait_for_timeout(500)
        tabs.nth(0).click()
        stats_page.wait_for_timeout(500)
        # First tab should render stats content
        stats_content = stats_page.locator(".stats-content")
        assert stats_content.count() > 0, "Stats content not rendered after tab switch"


def test_game_history_shows(stats_page):
    games_tab = stats_page.locator('.stats-tab:has-text("Games"), .stats-tab:has-text("History")')
    if games_tab.count() > 0:
        games_tab.click()
        stats_page.wait_for_timeout(500)
    game_cards = stats_page.locator(".stats-game-card")
    assert game_cards.count() > 0, "No game cards in history tab"


def test_expand_game_scoresheet(stats_page):
    expand_btn = stats_page.locator(".expand-game-btn, button:has-text('▶'), button:has-text('▸')")
    if expand_btn.count() > 0:
        expand_btn.first.click()
        stats_page.wait_for_timeout(500)
        scoresheet = stats_page.locator(".score-table-full, .scoresheet")
        if scoresheet.count() > 0:
            overflow = scoresheet.first.evaluate("el => getComputedStyle(el).overflowY")
            assert overflow in ("auto", "scroll", "visible")


def test_no_horizontal_overflow(stats_page):
    overflow = stats_page.evaluate(
        "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )
    assert not overflow
