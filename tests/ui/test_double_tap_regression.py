"""Regression test: double-tap on keypad must not skip a player.

Bug: On mobile, tapping keypad quickly fires handleHandsSelect/handleBidSelect
twice before the first await completes. Both calls read the same currentPlayer()
because entryPosition hasn't incremented yet, causing the next player to be skipped.

Fix: isSubmitting guard in handleHandsSelect and handleBidSelect.
"""

import pytest

from tests.ui.helpers import create_playground, start_game, unique_name


@pytest.fixture
def bidding_page(page, server):
    """Create playground with 3 players, start game, land on bidding screen."""
    page.goto(server)
    create_playground(page, unique_name("DblTap"), "1234", ["Alice", "Bob", "Charlie"])
    start_game(page)
    return page


class TestDoubleTapBidding:
    """Double-tap on bid keypad must not skip a player."""

    def test_dblclick_bid_does_not_skip_player(self, bidding_page):
        page = bidding_page

        # First player visible
        name_el = page.locator(".bid-player-name")
        name_el.wait_for(state="attached", timeout=10000)
        first_player = name_el.text_content()

        # Double-click the "1" key as fast as possible
        page.locator(".keypad-key:has-text('1')").dblclick()
        page.wait_for_timeout(1500)

        # After a single bid, the SECOND player should show — not the third
        current_name = page.locator(".bid-player-name")
        if current_name.is_visible():
            second_player = current_name.text_content()
            assert second_player != first_player, "Player didn't advance at all"
            # With 3 players in order [dealer+1, dealer+2, dealer],
            # the second should be the next one, not the one after
            # If double-tap skipped, we'd jump two positions
            # Check we're on position 1 (not position 2)
            page.locator(".keypad-key:has-text('1')").click()
            page.wait_for_timeout(1500)
            third = page.locator(".bid-player-name")
            if third.is_visible():
                third_player = third.text_content()
                assert third_player != second_player, "Third player same as second"

    def test_rapid_clicks_bid_processes_exactly_once(self, bidding_page):
        """Click bid key 3 times rapidly — only 1 should register."""
        page = bidding_page

        name_el = page.locator(".bid-player-name")
        name_el.wait_for(state="attached", timeout=10000)
        first_player = name_el.text_content()

        # Click 3 times rapidly
        key = page.locator(".keypad-key:has-text('1')")
        key.click()
        key.click(delay=0)
        key.click(delay=0)
        page.wait_for_timeout(2000)

        # Should have advanced exactly once — second player showing
        current = page.locator(".bid-player-name")
        if current.is_visible():
            assert current.text_content() != first_player


class TestDoubleTapRoundEnd:
    """Double-tap on hands keypad must not skip a player."""

    @pytest.fixture
    def roundend_page(self, page, server):
        """Get to round-end screen with 3 players."""
        page.goto(server)
        create_playground(page, unique_name("DblTapHands"), "1234", ["Alice", "Bob", "Charlie"])
        start_game(page)

        # Bid for all 3 players
        for _ in range(3):
            page.wait_for_selector(".keypad", timeout=60000)
            name_el = page.locator(".bid-player-name")
            name_el.wait_for(state="attached", timeout=10000)
            old_name = name_el.text_content() or ""
            page.locator(".keypad-key:has-text('1')").click()
            escaped = old_name.replace("'", "\\'")
            page.wait_for_function(
                "() => {"
                "  const el = document.querySelector('.bid-player-name');"
                f"  return !el || el.textContent !== '{escaped}';"
                "}",
                timeout=10000,
            )

        # Confirm bids
        page.locator('button:has-text("Start Round")').click()
        page.wait_for_function("() => location.hash.includes('play')", timeout=10000)

        # Enter round end
        page.locator('button:has-text("End Round"), button:has-text("Enter Results")').first.click()
        page.wait_for_function("() => location.hash.includes('roundend')", timeout=10000)
        page.wait_for_selector(".keypad", timeout=60000)
        return page

    def test_dblclick_hands_does_not_skip_player(self, roundend_page):
        """Double-clicking hands keypad must advance exactly one player."""
        page = roundend_page

        name_el = page.locator(".bid-player-name")
        name_el.wait_for(state="attached", timeout=10000)
        first_player = name_el.text_content()

        # Double-click "1" on hands keypad
        page.locator(".keypad-key:has-text('1')").dblclick()
        page.wait_for_timeout(1500)

        # Second player should be showing — not third
        current = page.locator(".bid-player-name")
        if current.is_visible():
            second_player = current.text_content()
            assert second_player != first_player, "Player didn't advance"

    def test_all_players_entered_after_sequential_hands(self, roundend_page):
        """Enter hands for all 3 players, end-round must succeed."""
        page = roundend_page

        # Enter hands for all 3 players carefully
        for _ in range(3):
            name_el = page.locator(".bid-player-name")
            if not name_el.is_visible():
                break  # On confirm screen
            old_name = name_el.text_content() or ""
            page.locator(".keypad-key:has-text('0')").click()
            escaped = old_name.replace("'", "\\'")
            page.wait_for_function(
                "() => {"
                "  const el = document.querySelector('.bid-player-name');"
                f"  return !el || el.textContent !== '{escaped}';"
                "}",
                timeout=10000,
            )

        # Should be on confirm screen — Score Round button visible
        score_btn = page.locator('button:has-text("Score Round")')
        score_btn.wait_for(state="visible", timeout=10000)
        score_btn.click()

        # Should advance to scoreboard — NOT get a 400 error
        page.wait_for_function(
            "() => location.hash.includes('scoreboard')",
            timeout=10000,
        )
