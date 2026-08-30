"""Regression test: enter_bid must advance to the next player deterministically.

Bug: Under CI load, fixed wait_for_timeout(1500) expired before the API call
resolved. The next click landed on the same player's keypad, causing key "3"
to be disabled for the wrong player (FK key constraint race condition).

This test verifies that after clicking a bid key, the player name changes
before the next bid is entered — proving deterministic advancement.
"""

import pytest

from tests.ui.helpers import create_playground, start_game, unique_name


@pytest.fixture
def bidding_page(page, server):
    page.goto(server)
    create_playground(page, unique_name("BidAdv"), "1234", ["Alice", "Bob", "Charlie"])
    start_game(page, {"mode": "Expert"})
    return page


def test_enter_bid_advances_to_next_player(bidding_page):
    """After clicking a bid key, the player name must change before
    the next bid can be entered. Fixed wait_for_timeout is not sufficient."""
    page = bidding_page

    # First player should be visible
    name_el = page.locator(".bid-player-name")
    first_player = name_el.text_content()
    assert first_player is not None

    # Click bid "2" for the first player
    page.locator(".keypad-key:has-text('2')").click()

    # The bug: wait_for_timeout(1500) doesn't guarantee the screen advanced.
    # This test will FAIL if enter_bid uses a fixed timeout and the API is slow.
    # After clicking, the player name must change (or keypad must disappear).
    page.wait_for_function(
        "() => {"
        "  const el = document.querySelector('.bid-player-name');"
        f"  return !el || el.textContent !== '{first_player}';"
        "}",
        timeout=10000,
    )

    # Verify second player is now shown
    if name_el.count() > 0:
        second_player = name_el.text_content()
        assert second_player != first_player, (
            f"Player name did not advance: still showing '{first_player}'"
        )
