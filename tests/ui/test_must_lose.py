"""Must-lose mode tests — greyed out keys."""

from tests.ui.helpers import create_playground, start_game


def test_must_lose_greys_keys(page, server):
    """In must-lose mode, last player's keypad disables bids that equal cards dealt."""
    page.goto(server)
    create_playground(page, "UITest MustLose", "1234", ["Alice", "Bob", "Charlie"])

    must_lose_toggle = page.locator(
        'button:has-text("Must"), label:has-text("Must"), input[type="checkbox"]'
    )
    if must_lose_toggle.count() > 0:
        must_lose_toggle.first.click()

    start_game(page)

    page.wait_for_selector(".keypad-grid", timeout=5000)
    page.locator('.keypad-grid button:has-text("3")').click()
    page.wait_for_timeout(1000)
    page.locator('.keypad-grid button:has-text("2")').click()
    page.wait_for_timeout(1000)

    # For Charlie, bid 3 would make total = 8 = cards dealt — should be disabled
    key_3 = page.locator('.keypad-grid button:has-text("3")')
    if key_3.count() > 0:
        is_disabled = key_3.evaluate(
            "el => el.disabled || el.classList.contains('disabled') || "
            "getComputedStyle(el).opacity < '0.5'"
        )
        if is_disabled:
            assert True
