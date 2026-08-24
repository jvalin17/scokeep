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
    url_hash = scoreboard_page.evaluate("() => location.hash")
    assert "scoreboard" in url_hash, f"Not on scoreboard: {url_hash}"
    score_table = scoreboard_page.locator(".score-table, .scoreboard")
    assert score_table.count() > 0, "No score display on scoreboard"


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


def test_undo_round_navigates_to_bidding(page, server):
    """Clicking #undo-round on the scoreboard navigates back to the bidding screen."""
    page.goto(server)
    create_playground(page, unique_name("Undo"), "1234", ["Alice", "Bob", "Charlie"])
    start_game(page)
    enter_bids_for_all(page, [2, 3, 1])
    confirm_bids(page)
    enter_hands_won(page, [2, 3, 3])

    score_btn = page.locator('button:has-text("Score Round")')
    score_btn.wait_for(state="visible", timeout=5000)
    score_btn.click()
    page.wait_for_function("() => location.hash.includes('scoreboard')", timeout=5000)

    undo_btn = page.locator("#undo-round")
    undo_btn.wait_for(state="visible", timeout=5000)
    undo_btn.click()

    page.wait_for_function("() => location.hash.includes('bid')", timeout=5000)
    url_hash = page.evaluate("() => location.hash")
    assert "bid" in url_hash, f"Expected hash to contain 'bid' after undo, got: {url_hash}"


def test_scoreboard_scores_correct(scoreboard_page):
    """Round scores match kachuful_standard rules: bid=made → N*10 (bid 1 → +11), missed → -11."""
    # bids=[2,3,1], hands=[2,3,3]
    # Player 0: bid 2, got 2 → +20
    # Player 1: bid 3, got 3 → +30
    # Player 2: bid 1, got 3 → missed → -11
    page = scoreboard_page
    content = page.content()
    assert "+20" in content, "Expected +20 for player 0 (bid 2 made)"
    assert "+30" in content, "Expected +30 for player 1 (bid 3 made)"
    assert "-11" in content, "Expected -11 for player 2 (bid 1 missed)"
    negative_cell = page.locator(".score-negative")
    assert negative_cell.count() > 0, "Expected at least one .score-negative cell"
