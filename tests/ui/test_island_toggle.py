"""Test: game island +/- toggle enlarges/shrinks text.

Requirement (project-state.md:29):
  + makes island text bigger (visibility from far)
  - returns to normal size
"""

from tests.ui.helpers import create_playground, start_game, unique_name


def test_island_toggle_default_shows_plus(page, server):
    """Default island state shows + button (not yet enlarged)."""
    page.goto(server)
    create_playground(page, unique_name("Toggle"), "1234", ["Alice", "Bob"])
    start_game(page, {"mode": "Friendly"})

    toggle = page.locator(".island-toggle")
    assert toggle.count() > 0, "Island toggle button not found"
    assert toggle.text_content().strip() == "+", (
        f"Default toggle should show '+', got '{toggle.text_content().strip()}'"
    )


def test_island_toggle_plus_enlarges_text(page, server):
    """Clicking + makes island text bigger, button changes to -."""
    page.goto(server)
    create_playground(page, unique_name("Enlarge"), "1234", ["Alice", "Bob"])
    start_game(page, {"mode": "Friendly"})

    island = page.locator(".game-island")
    toggle = page.locator(".island-toggle")

    # Get normal font size
    normal_size = island.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")

    # Click + to enlarge
    toggle.click()
    page.wait_for_timeout(300)

    enlarged_size = island.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
    assert enlarged_size > normal_size, (
        f"After clicking +, font should be bigger: got {enlarged_size}px, was {normal_size}px"
    )
    assert toggle.text_content().strip() == "−", (
        f"After enlarging, toggle should show '−', got '{toggle.text_content().strip()}'"
    )


def test_island_toggle_minus_returns_to_normal(page, server):
    """Clicking - after + returns to normal size."""
    page.goto(server)
    create_playground(page, unique_name("Shrink"), "1234", ["Alice", "Bob"])
    start_game(page, {"mode": "Friendly"})

    island = page.locator(".game-island")
    toggle = page.locator(".island-toggle")

    normal_size = island.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")

    # Click + to enlarge, then - to return
    toggle.click()
    page.wait_for_timeout(300)
    toggle.click()
    page.wait_for_timeout(300)

    restored_size = island.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
    assert restored_size == normal_size, (
        f"After clicking -, font should return to {normal_size}px, got {restored_size}px"
    )
    assert toggle.text_content().strip() == "+", (
        f"After shrinking, toggle should show '+', got '{toggle.text_content().strip()}'"
    )
