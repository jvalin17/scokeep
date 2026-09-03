"""Regression test: going back during hands entry must clear subsequent entries.

Bug: After entering hands for multiple players and going back, the claimed
count still includes entries from players after the current position.
"""

from tests.ui.helpers import (
    confirm_bids,
    create_playground,
    enter_bid,
    start_game,
    unique_name,
)


def test_hands_count_clears_subsequent_on_back(page, server):
    """Going back to a previous player must clear all subsequent hands entries
    so the count only reflects players up to the current position."""
    page.goto(server)
    create_playground(page, unique_name("HandsBack"), "1234", ["Alice", "Bob", "Candy"])
    start_game(page, {"mode": "Expert"})

    # Enter bids (round 1 = 8 cards)
    enter_bid(page, 2)
    page.wait_for_selector(".keypad", timeout=30000)
    enter_bid(page, 3)
    page.wait_for_selector(".keypad", timeout=30000)
    enter_bid(page, 1)
    confirm_bids(page)

    # Go to roundend
    end_round_btn = page.locator('button:has-text("End Round"), button:has-text("Enter Results")')
    end_round_btn.first.click()
    page.wait_for_function("() => location.hash.includes('roundend')", timeout=10000)

    # Enter hands: Alice=3, Bob=2
    page.wait_for_selector(".keypad", timeout=30000)
    enter_bid(page, 3)
    page.wait_for_selector(".keypad", timeout=30000)
    enter_bid(page, 2)

    # Now on Candy (position 2, last player). Go back to Bob.
    page.wait_for_selector("#go-back", timeout=5000)

    # Capture Candy's name before clicking back
    candy_name = page.locator(".bid-player-name").text_content()
    page.click("#go-back")

    # Wait for player name to change (back to Bob)
    escaped = candy_name.replace("'", "\\'")
    page.wait_for_function(
        "() => {"
        "  const el = document.querySelector('.bid-player-name');"
        f"  return el && el.textContent !== '{escaped}';"
        "}",
        timeout=10000,
    )

    # Check: claimed should show only Alice's 3 (Bob cleared on back)
    claimed = page.locator(".claimed-info").text_content()
    assert "3 of 8" in claimed, (
        f"After going back to Bob, claimed should show '3 of 8' (only Alice), got: '{claimed}'"
    )


def test_hands_back_clears_subsequent_entries(page, server):
    """Going back from player 3 to player 2 must also clear player 3's entry.

    With 3 players and 8 cards: enter Alice=3, Bob=2. Now on Candy (last).
    Candy's remaining = 3 (auto-fill). After Candy enters, go back via
    confirm screen Edit on the first player — total should reset properly.
    """
    page.goto(server)
    create_playground(page, unique_name("HandsClear"), "1234", ["Alice", "Bob", "Candy"])
    start_game(page, {"mode": "Expert"})

    # Enter bids
    enter_bid(page, 2)
    page.wait_for_selector(".keypad", timeout=30000)
    enter_bid(page, 3)
    page.wait_for_selector(".keypad", timeout=30000)
    enter_bid(page, 1)
    confirm_bids(page)

    # Go to roundend
    end_round_btn = page.locator('button:has-text("End Round"), button:has-text("Enter Results")')
    end_round_btn.first.click()
    page.wait_for_function("() => location.hash.includes('roundend')", timeout=10000)

    # Enter hands for first two players
    page.wait_for_selector(".keypad", timeout=30000)
    enter_bid(page, 3)
    page.wait_for_selector(".keypad", timeout=30000)
    enter_bid(page, 2)

    # Now on last player. Click back to go to player 2.
    page.wait_for_selector("#go-back", timeout=5000)
    old_name = page.locator(".bid-player-name").text_content()
    page.click("#go-back")
    escaped = old_name.replace("'", "\\'")
    page.wait_for_function(
        "() => {"
        "  const el = document.querySelector('.bid-player-name');"
        f"  return el && el.textContent !== '{escaped}';"
        "}",
        timeout=10000,
    )

    # Now enter 1 for player 2 (changed from 2 to 1)
    enter_bid(page, 1)

    # Now on last player again. Check claimed = first(3) + second(1) = 4
    page.wait_for_selector(".claimed-info", timeout=5000)
    claimed = page.locator(".claimed-info").text_content()
    assert "4 of 8" in claimed, (
        f"After re-entering player 2 as 1, claimed should be '4 of 8' (3+1), got: '{claimed}'"
    )
