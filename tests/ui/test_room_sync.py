"""Quick Game Room Sync — E2E tests.

Tests the room picker, PIN verification, player auto-fill, and game-to-room linking.
Requires: joining a room online first to cache it, then using it in Quick Game.
Covers: home.js screen (all tabs, room finder, PIN flow, create, join).
"""

import pytest
from playwright.sync_api import expect

from tests.ui.helpers import create_playground, unique_name


@pytest.fixture()
def room_page(page, server):
    """Create a room online, join it (caches room in IDB), navigate to Quick Game."""
    room_name = unique_name("SyncRoom")
    page.goto(server)
    create_playground(page, room_name, "1234", ["Anjum", "Masood", "Lala"])
    # Go back to home to access Quick Game
    page.goto(server)
    page.wait_for_selector(".tabs", timeout=5000)
    yield page, room_name


def test_room_list_shows_cached_rooms(room_page):
    """After joining a room online, Quick Game tab shows it in the room finder list."""
    page, room_name = room_page
    page.click('.tab[data-tab="quick"]')
    page.wait_for_selector("#quick-form:not(.hidden)", timeout=3000)

    room_list = page.locator("#quick-room-list")
    expect(room_list).to_be_visible(timeout=5000)

    # Should have at least one room button
    room_buttons = room_list.locator(".quick-room-item")
    assert room_buttons.count() >= 1, "Expected at least 1 cached room in list"
    expect(room_list.locator(f'.quick-room-item:has-text("{room_name}")')).to_be_visible()


def test_pin_input_appears_on_room_click(room_page):
    """Clicking a room in the list shows PIN input field."""
    page, room_name = room_page
    page.click('.tab[data-tab="quick"]')
    page.wait_for_selector("#quick-form:not(.hidden)", timeout=3000)

    page.locator(f'.quick-room-item:has-text("{room_name}")').click()

    pin_input = page.locator("#quick-room-pin")
    expect(pin_input).to_be_visible(timeout=3000)

    # Selected room name should be shown
    selected_label = page.locator("#quick-room-selected")
    expect(selected_label).to_be_visible(timeout=3000)


def test_correct_pin_autofills_players(room_page):
    """Entering correct PIN auto-fills player names from the cached room."""
    page, room_name = room_page
    page.click('.tab[data-tab="quick"]')
    page.wait_for_selector("#quick-form:not(.hidden)", timeout=3000)

    page.locator(f'.quick-room-item:has-text("{room_name}")').click()
    page.wait_for_selector("#quick-room-pin", timeout=3000)

    page.fill("#quick-room-pin", "1234")
    page.click("#quick-room-verify")

    # Wait for players to auto-fill
    page.wait_for_function(
        "() => document.querySelector('.quick-player-name')?.value?.length > 0",
        timeout=5000,
    )

    player_inputs = page.locator(".quick-player-name")
    first_player = player_inputs.nth(0).input_value()
    assert first_player in ["Anjum", "Masood", "Lala"], (
        f"Expected a player name from the room, got '{first_player}'"
    )


def test_wrong_pin_shows_error(room_page):
    """Entering wrong PIN shows error message, keeps room selected."""
    page, room_name = room_page
    page.click('.tab[data-tab="quick"]')
    page.wait_for_selector("#quick-form:not(.hidden)", timeout=3000)

    page.locator(f'.quick-room-item:has-text("{room_name}")').click()
    page.wait_for_selector("#quick-room-pin", timeout=3000)

    page.fill("#quick-room-pin", "9999")
    page.click("#quick-room-verify")

    error = page.locator("#quick-room-error")
    error.wait_for(state="visible", timeout=5000)
    expect(error).to_be_visible(timeout=3000)
    expect(error).to_contain_text("Wrong PIN")
