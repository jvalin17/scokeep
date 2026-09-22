"""Test: game island (round info bar) must be large enough to read.

The game island shows R1/24, trump suit, and cards dealt. It should
have a minimum font size for readability on mobile.
"""

from tests.ui.helpers import create_playground, start_game, unique_name


def test_game_island_font_size(page, server):
    """Game island text must be at least 14px for readability."""
    page.goto(server)
    create_playground(page, unique_name("Island"), "1234", ["Alice", "Bob"])
    start_game(page, {"mode": "Friendly"})

    island = page.locator(".game-island")
    assert island.count() > 0, "Game island not found on bidding screen"

    font_size = island.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
    assert font_size >= 18, f"Game island font size is {font_size}px, should be >= 18px"

    padding = island.evaluate("el => parseFloat(getComputedStyle(el).paddingTop)")
    assert padding >= 14, f"Game island padding is {padding}px, should be >= 14px"


def test_island_toggle_enlarges_not_hides(page, server):
    """+ makes island bigger, - returns to normal. Text must never vanish."""
    page.goto(server)
    create_playground(page, unique_name("Toggle"), "1234", ["Alice", "Bob"])
    start_game(page, {"mode": "Friendly"})

    island = page.locator(".game-island")
    toggle = page.locator(".island-toggle")
    assert toggle.count() > 0, "Toggle button not found"

    # Get normal size
    normal_size = island.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
    assert normal_size >= 14, f"Normal size too small: {normal_size}px"

    # Click + to enlarge
    if toggle.inner_text() == "+":
        toggle.click()
        js_bigger = (
            f"() => parseFloat(getComputedStyle("
            f"document.querySelector('.game-island')).fontSize) > {normal_size}"
        )
        page.wait_for_function(js_bigger, timeout=3000)

    # Enlarged: font must be bigger than normal
    enlarged_size = island.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
    assert enlarged_size > normal_size, (
        f"Enlarged {enlarged_size}px should be bigger than normal {normal_size}px"
    )

    # All spans must still be visible (not hidden)
    spans = island.locator("span")
    for i in range(spans.count()):
        display = spans.nth(i).evaluate("el => getComputedStyle(el).display")
        assert display != "none", f"Span {i} is hidden after enlarge"

    # Click - to return to normal
    toggle.click()
    js_near = (
        f"() => Math.abs(parseFloat(getComputedStyle("
        f"document.querySelector('.game-island')).fontSize) - {normal_size}) < 2"
    )
    page.wait_for_function(js_near, timeout=3000)
    restored_size = island.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
    assert abs(restored_size - normal_size) < 2, (
        f"Restored {restored_size}px should match normal {normal_size}px"
    )
