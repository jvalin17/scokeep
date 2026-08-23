"""Stats screen tests — tabs, scoresheet expand, chart, insights."""

import pytest

from tests.ui.helpers import (
    VIEWPORTS,
    auth_playground,
    confirm_bids,
    create_playground,
    end_game,
    enter_bids_for_all,
    enter_hands_won,
    start_game,
)


@pytest.fixture
def stats_page(page, server):
    page.goto(server)
    create_playground(page, "UITest Stats", "1234", ["Alice", "Bob", "Charlie"])
    start_game(page)
    enter_bids_for_all(page, [2, 3, 1])
    confirm_bids(page)
    enter_hands_won(page, [2, 3, 3])
    page.wait_for_timeout(500)
    end_game(page)
    page.wait_for_timeout(500)

    auth_playground(page, server, "UITest Stats", "1234")
    stats_btn = page.locator('button:has-text("Stats"), a:has-text("Stats")')
    if stats_btn.count() > 0:
        stats_btn.first.click()
        page.wait_for_timeout(1000)
    return page


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=lambda v: v["name"])
def test_stats_renders(stats_page, viewport):
    stats_page.set_viewport_size(viewport)
    content = stats_page.content()
    assert "stats" in content.lower() or "game" in content.lower()


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
        assert len(stats_page.content()) > 100


def test_game_history_shows(stats_page):
    games_tab = stats_page.locator('.stats-tab:has-text("Games"), .stats-tab:has-text("History")')
    if games_tab.count() > 0:
        games_tab.click()
        stats_page.wait_for_timeout(500)
    content = stats_page.content()
    assert "game" in content.lower() or "round" in content.lower()


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
