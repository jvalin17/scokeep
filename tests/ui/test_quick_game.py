"""Quick Game — local-engine E2E tests via Playwright.

Quick Game uses game-api.js (local IndexedDB engine) with string IDs
starting with 'game-'. No server round-trip for game logic.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.fixture()
def qg_page(page, server):
    """Navigate to home screen for Quick Game tests."""
    page.goto(server)
    yield page


def start_quick_game(page: Page, players: list[str]):
    """Navigate to Quick Game tab and start a game."""
    page.wait_for_selector(".tabs", timeout=5000)
    page.click('.tab[data-tab="quick"]')
    page.wait_for_selector("#quick-form:not(.hidden)", timeout=3000)

    inputs = page.locator(".quick-player-name")
    for i, name in enumerate(players):
        if i < inputs.count():
            inputs.nth(i).fill(name)
        else:
            page.click("#quick-add-player")
            page.locator(".quick-player-name").last.fill(name)

    page.click("#quick-start")
    page.wait_for_function(
        "() => location.hash.includes('bid/game-')",
        timeout=10000,
    )


def test_quick_game_starts_with_local_id(qg_page):
    """Quick Game creates a game with a 'game-' prefixed ID."""
    start_quick_game(qg_page, ["Alice", "Bob", "Charlie"])
    game_hash = qg_page.evaluate("() => location.hash")
    assert "game-" in game_hash
    # Should show bidding screen
    expect(qg_page.locator(".bid-player-name")).to_be_visible(timeout=5000)


def play_quick_round(page: Page, num_players: int):
    """Play one round for a quick game: bid 0 for all, hands 0 for first N-1, rest for last."""
    # Bid 0 for each player
    for _ in range(num_players):
        page.wait_for_selector(".keypad", timeout=10000)
        name_el = page.locator(".bid-player-name")
        name_el.wait_for(state="attached", timeout=10000)
        old_name = name_el.text_content() or ""
        page.locator(".keypad-key:has-text('0')").click()
        escaped = old_name.replace("'", "\\'")
        page.wait_for_function(
            "() => { const el = document.querySelector('.bid-player-name');"
            f" return !el || el.textContent !== '{escaped}'; }}",
            timeout=10000,
        )

    # Confirm bids
    page.locator('button:has-text("Start Round")').wait_for(state="visible", timeout=10000)
    page.locator('button:has-text("Start Round")').click()
    page.wait_for_function("() => location.hash.includes('play')", timeout=10000)

    # End round → roundend
    page.locator('button:has-text("End Round")').click()
    page.wait_for_function("() => location.hash.includes('roundend')", timeout=10000)

    # Enter hands won — 0 for first N-1 players, last player is auto-forced to remaining
    for i in range(num_players):
        page.wait_for_selector(".keypad", timeout=10000)
        name_el = page.locator(".bid-player-name")
        name_el.wait_for(state="attached", timeout=10000)
        old_name = name_el.text_content() or ""
        if i < num_players - 1:
            page.locator(".keypad-key:has-text('0')").click()
        else:
            # Last player: only 'remaining' key is enabled — click the enabled one
            page.locator(".keypad-key:not([disabled])").first.click()
        escaped = old_name.replace("'", "\\'")
        page.wait_for_function(
            "() => { const el = document.querySelector('.bid-player-name');"
            f" return !el || el.textContent !== '{escaped}'; }}",
            timeout=10000,
        )

    # Score round
    page.locator('button:has-text("Score Round")').wait_for(state="visible", timeout=10000)
    page.locator('button:has-text("Score Round")').click()
    page.wait_for_function("() => location.hash.includes('scoreboard')", timeout=10000)


def test_quick_game_full_round(qg_page):
    """Play one complete round in Quick Game mode."""
    start_quick_game(qg_page, ["Alice", "Bob"])
    play_quick_round(qg_page, 2)
    expect(qg_page.locator(".scoreboard")).to_be_visible(timeout=5000)


def test_quick_game_end_game(qg_page):
    """Start Quick Game, play a round, then end the game via review screen."""
    start_quick_game(qg_page, ["Alice", "Bob"])
    play_quick_round(qg_page, 2)

    # End the game from scoreboard
    qg_page.locator("#end-game").click()
    qg_page.wait_for_function(
        "() => location.hash.includes('review')",
        timeout=10000,
    )

    # Confirm final scores on review screen
    qg_page.locator("#confirm-final").wait_for(state="visible", timeout=10000)
    qg_page.locator("#confirm-final").click()
    qg_page.wait_for_function(
        "() => location.hash.includes('scoreboard')",
        timeout=10000,
    )

    # Game over scoreboard shows celebration with confetti and trophy
    expect(qg_page.locator(".final-celebration, .final-trophy").first).to_be_visible(timeout=10000)
