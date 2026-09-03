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
