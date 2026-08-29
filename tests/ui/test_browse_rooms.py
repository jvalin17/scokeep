"""Browse Rooms UI tests — browse button, filter, room selection."""

from tests.ui.helpers import create_playground, unique_name


def test_browse_button_visible_on_join_tab(page, server):
    """Browse All Rooms button is visible on the join tab."""
    page.goto(server)
    page.click('.tab[data-tab="join"]')
    browse_btn = page.locator("#browse-rooms-btn")
    browse_btn.wait_for(state="visible", timeout=5000)
    assert browse_btn.is_visible()


def test_browse_button_has_pill_styling(page, server):
    """Browse button must have .browse-toggle class for capsule pill styling."""
    page.goto(server)
    page.click('.tab[data-tab="join"]')
    browse_btn = page.locator("#browse-rooms-btn")
    browse_btn.wait_for(state="visible", timeout=5000)
    has_class = browse_btn.evaluate("el => el.classList.contains('browse-toggle')")
    assert has_class, "Browse button must have .browse-toggle class"
    border_radius = browse_btn.evaluate("el => getComputedStyle(el).borderRadius")
    assert border_radius == "22px", f"Expected 22px border-radius for pill, got: {border_radius}"


def test_browse_toggle_closes_on_second_click(page, server):
    """Clicking browse button again closes the panel."""
    page.goto(server)
    create_playground(page, unique_name("ToggleTest"), "1234", ["Alice", "Bob"])
    page.goto(server)
    page.click('.tab[data-tab="join"]')

    # Open
    page.click("#browse-rooms-btn")
    page.wait_for_selector(".browse-item", timeout=5000)
    assert page.locator("#browse-rooms").is_visible()

    # Close
    page.click("#browse-rooms-btn")
    page.wait_for_timeout(300)
    assert page.locator("#browse-rooms").is_hidden(), "Browse panel should hide on second click"


def test_browse_shows_rooms_on_click(page, server):
    """Clicking Browse shows all rooms as capsule pills."""
    page.goto(server)
    create_playground(page, unique_name("BrowseTest"), "1234", ["Alice", "Bob"])
    page.goto(server)
    page.click('.tab[data-tab="join"]')

    page.click("#browse-rooms-btn")
    page.wait_for_selector(".browse-item", timeout=5000)
    items = page.locator(".browse-item")
    assert items.count() > 0, "No browse items rendered"


def test_browse_filter_narrows_results(page, server):
    """Typing in filter narrows the room list."""
    page.goto(server)
    create_playground(page, unique_name("FilterAlpha"), "1234", ["Maria", "Carlos"])
    page.goto(server)
    create_playground(page, unique_name("FilterBeta"), "1234", ["Wei", "Nadia"])
    page.goto(server)
    page.click('.tab[data-tab="join"]')
    page.click("#browse-rooms-btn")
    page.wait_for_selector(".browse-item", timeout=5000)

    # Should show both rooms initially
    all_items = page.locator(".browse-item")
    initial_count = all_items.count()
    assert initial_count >= 2

    # Type player name to filter
    page.fill("#browse-filter", "Maria")
    page.wait_for_timeout(300)
    filtered = page.locator(".browse-item")
    assert filtered.count() < initial_count, "Filter did not narrow results"
    assert filtered.count() >= 1, "Filter removed all results"


def test_browse_click_populates_join_name(page, server):
    """Clicking a browse item populates the join-name field."""
    page.goto(server)
    create_playground(page, unique_name("ClickRoom"), "1234", ["Alice", "Bob"])
    page.goto(server)
    page.click('.tab[data-tab="join"]')
    page.click("#browse-rooms-btn")
    page.wait_for_selector(".browse-item", timeout=5000)

    page.locator(".browse-item").first.click()
    join_name = page.locator("#join-name")
    assert join_name.input_value() != "", (
        "Join name field should be populated after clicking a room"
    )

    # Browse panel should be hidden after selection
    browse_panel = page.locator("#browse-rooms")
    assert browse_panel.is_hidden(), "Browse panel should hide after selection"

    # PIN field should be focused
    focused = page.evaluate("() => document.activeElement.id")
    assert focused == "join-pin", f"Expected PIN field focused, got: {focused}"
