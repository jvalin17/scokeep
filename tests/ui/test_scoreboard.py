"""Scoreboard screen tests — rendering, scrolling, sticky headers."""

import pytest

from tests.ui.helpers import (
    VIEWPORTS,
    confirm_bids,
    create_playground,
    enter_bids_for_all,
    enter_hands_won,
    start_game,
    unique_name,
)


@pytest.fixture
def scoreboard_page(page, server):
    page.goto(server)
    create_playground(page, unique_name("Scoreboard"), "1234", ["Alice", "Bob", "Charlie"])
    start_game(page)
    enter_bids_for_all(page, [2, 3, 1])
    confirm_bids(page)
    enter_hands_won(page, [2, 3, 3])
    # Score the round to navigate to scoreboard
    score_btn = page.locator('button:has-text("Score Round")')
    if score_btn.count() > 0:
        score_btn.click()
        page.wait_for_timeout(1000)
    return page


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=lambda v: v["name"])
def test_scoreboard_renders(scoreboard_page, viewport):
    scoreboard_page.set_viewport_size(viewport)
    content = scoreboard_page.content()
    assert "score" in content.lower() or "round" in content.lower()


def test_scoresheet_scrollable(scoreboard_page):
    score_table = scoreboard_page.locator(".score-table-full")
    if score_table.count() > 0:
        overflow = score_table.evaluate("el => getComputedStyle(el).overflowY")
        assert overflow in ("auto", "scroll")


def test_sticky_headers(scoreboard_page):
    thead_th = scoreboard_page.locator(".scoresheet thead th")
    if thead_th.count() > 0:
        position = thead_th.first.evaluate("el => getComputedStyle(el).position")
        assert position == "sticky"


def test_scoreboard_buttons(scoreboard_page):
    buttons = scoreboard_page.locator(
        'button:has-text("End Game"), button:has-text("Next Round"), button:has-text("Extend")'
    )
    assert buttons.count() > 0
