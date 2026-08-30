"""Must-lose mode tests — forbidden key disabled for last bidder."""

from tests.ui.helpers import create_playground, enter_bid, start_game, unique_name


def test_must_lose_forbidden_key_disabled(page, server):
    """Last bidder's keypad disables the forbidden bid.

    Setup: 3 players, 8 cards dealt (default first round).
    Player 0 bids 5, Player 1 bids 2 → sum = 7.
    Forbidden for Player 2 (dealer/last) = 8 - 7 = 1.
    Assert key 1 is disabled and key 0 is NOT disabled.
    """
    page.goto(server)
    create_playground(page, unique_name("MustLose"), "1234", ["Alice", "Bob", "Charlie"])
    start_game(page)

    # Player 0 bids 5, Player 1 bids 2
    enter_bid(page, 5)
    page.wait_for_selector(".keypad", timeout=15000)
    enter_bid(page, 2)

    # Player 2 is now the last bidder — forbidden key = 8 - (5+2) = 1
    page.wait_for_selector(".keypad", timeout=15000)

    key_1 = page.locator('.keypad-key:has-text("1")')
    key_1.wait_for(state="attached", timeout=3000)
    is_key_1_disabled = key_1.evaluate(
        "el => el.disabled === true || el.classList.contains('keypad-disabled')"
    )
    assert is_key_1_disabled, "Key '1' (forbidden bid) must be disabled for the last player"

    key_0 = page.locator('.keypad-key:has-text("0")')
    key_0.wait_for(state="attached", timeout=3000)
    is_key_0_disabled = key_0.evaluate(
        "el => el.disabled === true || el.classList.contains('keypad-disabled')"
    )
    assert not is_key_0_disabled, "Key '0' (non-forbidden bid) must NOT be disabled"
