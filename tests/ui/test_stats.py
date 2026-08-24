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


def test_stats_empty_state(page, server):
    """A brand-new playground with no games shows the empty-state message, not stats tabs."""
    page.goto(server)
    create_playground(page, unique_name("EmptyStats"), "1234", ["Alice", "Bob", "Charlie"])
    page.wait_for_selector("#view-stats", timeout=5000)
    page.click("#view-stats")
    page.wait_for_selector(".stats-empty", timeout=5000)

    empty_msg = page.locator(".stats-empty")
    assert empty_msg.is_visible(), ".stats-empty element not visible for a playground with no games"
    text = empty_msg.inner_text()
    assert "No games" in text or "no games" in text.lower(), (
        f"Empty state text does not mention 'No games': {text!r}"
    )

    tabs = page.locator(".stats-tab")
    assert tabs.count() == 0, (
        f"Expected no .stats-tab elements in empty state, found {tabs.count()}"
    )


def test_personality_card_flip(stats_page):
    """Personality cards toggle .flipped on click; locked cards do NOT flip."""
    page = stats_page

    # Navigate to Insights tab (default, but be explicit)
    insights_tab = page.locator('.stats-tab:has-text("Insights"), .stats-tab:has-text("Players")')
    if insights_tab.count() > 0:
        insights_tab.first.click()
        page.wait_for_timeout(500)

    unlocked = page.locator(".personality-card:not(.personality-card-locked)")
    locked = page.locator(".personality-card-locked")

    if unlocked.count() > 0:
        # Unlocked card: clicking it must toggle .flipped
        card = unlocked.first
        card.click()
        page.wait_for_timeout(700)
        has_flipped = card.evaluate("el => el.classList.contains('flipped')")
        assert has_flipped, "Clicking an unlocked .personality-card must add .flipped class"

        # Click again to flip back
        card.click()
        page.wait_for_timeout(700)
        still_flipped = card.evaluate("el => el.classList.contains('flipped')")
        assert not still_flipped, "Second click must remove .flipped from .personality-card"
    else:
        # After 1 game only locked cards exist — assert they are present and do NOT flip
        assert locked.count() > 0, "Expected .personality-card-locked when no unlocked cards exist"
        locked.first.click()
        page.wait_for_timeout(700)
        flipped = page.locator(".personality-card-locked.flipped")
        assert flipped.count() == 0, "Locked card must not gain .flipped class when clicked"


def test_locked_personality_card(page, server):
    """After 1 game (< 3 required), insights tab shows locked cards that cannot be flipped."""
    name = unique_name("Locked")
    page.goto(server)
    create_playground(page, name, "1234", ["Alice", "Bob", "Charlie"])
    start_game(page)
    enter_bids_for_all(page, [2, 3, 1])
    confirm_bids(page)
    enter_hands_won(page, [2, 3, 3])
    score_btn = page.locator('button:has-text("Score Round")')
    if score_btn.count() > 0:
        score_btn.click()
        page.wait_for_timeout(1000)
    end_game(page)
    page.wait_for_timeout(500)

    navigate_to_stats(page, server, name, "1234")

    # Insights tab is active by default — assert locked cards are present
    locked_card = page.locator(".personality-card-locked")
    assert locked_card.count() > 0, "Expected .personality-card-locked with only 1 game played"

    unlock_text = page.locator(".personality-unlock-text")
    assert unlock_text.count() > 0, "Expected .personality-unlock-text to be rendered"
    text_content = unlock_text.first.inner_text()
    assert "1/" in text_content, f"Expected '1/' in unlock text, got: {text_content!r}"

    # Click a locked card — it must NOT get .flipped class
    locked_card.first.click()
    page.wait_for_timeout(700)
    flipped = page.locator(".personality-card-locked.flipped")
    assert flipped.count() == 0, "Locked card should not flip when clicked"
