"""Browse Rooms UI tests — room finder panel, filters, room selection."""

from tests.ui.helpers import create_playground, unique_name


def test_room_finder_visible_on_join_tab(page, server):
    """Room finder card is visible on the join tab."""
    page.goto(server)
    page.click('.tab[data-tab="join"]')
    finder = page.locator(".room-finder")
    finder.wait_for(state="visible", timeout=5000)
    assert finder.is_visible()


def test_browse_toggle_visible(page, server):
    """Browse all link is visible in the room finder header."""
    page.goto(server)
    page.click('.tab[data-tab="join"]')
    browse_btn = page.locator("#browse-rooms-btn")
    browse_btn.wait_for(state="visible", timeout=5000)
    assert browse_btn.is_visible()
    has_class = browse_btn.evaluate("el => el.classList.contains('browse-toggle')")
    assert has_class, "Browse button must have .browse-toggle class"


def test_browse_shows_two_filter_inputs(page, server):
    """Expanding browse shows room name and player name filter inputs."""
    page.goto(server)
    create_playground(page, unique_name("FilterTest"), "1234", ["Alice", "Bob"])
    page.goto(server)
    page.click('.tab[data-tab="join"]')
    page.click("#browse-rooms-btn")
    page.wait_for_selector(".browse-item", timeout=5000)

    room_filter = page.locator("#browse-filter-room")
    player_filter = page.locator("#browse-filter-player")
    assert room_filter.is_visible(), "Room name filter should be visible"
    assert player_filter.is_visible(), "Player name filter should be visible"


def test_browse_hides_recent_rooms(page, server):
    """Recent rooms are hidden when browse panel is open."""
    page.goto(server)
    create_playground(page, unique_name("HideRecent"), "1234", ["Alice", "Bob"])
    page.goto(server)
    page.click('.tab[data-tab="join"]')

    # Recent should be visible before browse
    page.wait_for_timeout(500)

    page.click("#browse-rooms-btn")
    page.wait_for_selector(".browse-item", timeout=5000)
    recent = page.locator("#recent-playgrounds")
    assert recent.is_hidden(), "Recent rooms should be hidden when browse is open"


def test_browse_toggle_closes_on_second_click(page, server):
    """Clicking browse again closes the panel and restores recent."""
    page.goto(server)
    create_playground(page, unique_name("ToggleClose"), "1234", ["Alice", "Bob"])
    page.goto(server)
    page.click('.tab[data-tab="join"]')

    page.click("#browse-rooms-btn")
    page.wait_for_selector(".browse-item", timeout=5000)
    assert page.locator("#browse-rooms").is_visible()

    page.click("#browse-rooms-btn")
    page.wait_for_timeout(300)
    assert page.locator("#browse-rooms").is_hidden(), "Browse should hide on second click"


def test_filter_by_room_name(page, server):
    """Room name filter narrows results by room name."""
    page.goto(server)
    create_playground(page, unique_name("RoomAlpha"), "1234", ["Alice", "Bob"])
    page.goto(server)
    create_playground(page, unique_name("RoomBeta"), "1234", ["Carlos", "Wei"])
    page.goto(server)
    page.click('.tab[data-tab="join"]')
    page.click("#browse-rooms-btn")
    page.wait_for_selector(".browse-item", timeout=5000)

    initial_count = page.locator(".browse-item").count()
    assert initial_count >= 2

    page.fill("#browse-filter-room", "Alpha")
    page.wait_for_timeout(300)
    filtered = page.locator(".browse-item")
    assert filtered.count() < initial_count, "Room filter did not narrow results"
    assert filtered.count() >= 1


def test_filter_by_player_name(page, server):
    """Player name filter narrows results by player name."""
    page.goto(server)
    create_playground(page, unique_name("PlayerAlpha"), "1234", ["Maria", "Carlos"])
    page.goto(server)
    create_playground(page, unique_name("PlayerBeta"), "1234", ["Wei", "Nadia"])
    page.goto(server)
    page.click('.tab[data-tab="join"]')
    page.click("#browse-rooms-btn")
    page.wait_for_selector(".browse-item", timeout=5000)

    initial_count = page.locator(".browse-item").count()
    page.fill("#browse-filter-player", "Maria")
    page.wait_for_timeout(300)
    filtered = page.locator(".browse-item")
    assert filtered.count() < initial_count, "Player filter did not narrow results"
    assert filtered.count() >= 1


def test_browse_click_populates_join_name(page, server):
    """Clicking a browse item populates join-name and focuses PIN."""
    page.goto(server)
    create_playground(page, unique_name("ClickSelect"), "1234", ["Alice", "Bob"])
    page.goto(server)
    page.click('.tab[data-tab="join"]')
    page.click("#browse-rooms-btn")
    page.wait_for_selector(".browse-item", timeout=5000)

    page.locator(".browse-item").first.click()
    join_name = page.locator("#join-name")
    assert join_name.input_value() != "", "Join name should be populated"

    browse_panel = page.locator("#browse-rooms")
    assert browse_panel.is_hidden(), "Browse panel should hide after selection"

    focused = page.evaluate("() => document.activeElement.id")
    assert focused == "join-pin", f"Expected PIN focused, got: {focused}"
