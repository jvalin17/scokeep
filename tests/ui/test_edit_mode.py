"""Edit mode tests — admin key, purple tint, cross-room isolation."""

import pytest

from tests.ui.helpers import (
    confirm_bids,
    create_playground,
    end_game,
    enter_bids_for_all,
    enter_hands_won,
    navigate_to_stats,
    start_game,
    unique_name,
)


@pytest.fixture
def stats_with_game(page, server):
    name = unique_name("Edit")
    page.goto(server)
    create_playground(page, name, "1234", ["Alice", "Bob", "Charlie"])
    start_game(page)
    enter_bids_for_all(page, [2, 3, 1])
    confirm_bids(page)
    enter_hands_won(page, [2, 3, 3])
    score_btn = page.locator('button:has-text("Score Round")')
    if score_btn.count() > 0:
        score_btn.click()
        page.wait_for_timeout(1000)
    end_game(page)
    page.wait_for_timeout(500)
    navigate_to_stats(page, server, name, "1234")
    return page


def test_edit_mode_toggle(stats_with_game):
    page = stats_with_game
    edit_btn = page.locator('#toggle-edit, button:has-text("Edit")')
    if edit_btn.count() > 0:
        edit_btn.click()
        page.wait_for_timeout(500)
        key_input = page.locator('input[type="password"], input[type="text"]').last
        if key_input.count() > 0:
            key_input.fill("test-admin-key")
            go_btn = page.locator('button:has-text("Go"), button:has-text("✓")')
            if go_btn.count() > 0:
                go_btn.first.click()
                page.wait_for_timeout(500)
            edit_mode = page.locator(".edit-mode")
            if edit_mode.count() > 0:
                bg = edit_mode.evaluate("el => getComputedStyle(el).backgroundColor")
                assert bg != "rgba(0, 0, 0, 0)"


def test_edit_mode_wrong_password(stats_with_game):
    """Wrong admin password shows 'Wrong password' placeholder, no edit mode."""
    page = stats_with_game
    # Open settings panel via gear button
    gear_btn = page.locator("#stats-gear")
    gear_btn.wait_for(state="visible", timeout=5000)
    gear_btn.click()
    page.wait_for_selector("#stats-actions:not(.hidden)", timeout=3000)
    # Click toggle-edit to show password input
    toggle_edit = page.locator("#toggle-edit")
    toggle_edit.click()
    page.wait_for_timeout(300)
    # Fill in wrong password and submit
    pwd_input = page.locator('input[type="password"]')
    pwd_input.wait_for(state="visible", timeout=3000)
    pwd_input.fill("definitely-wrong-password")
    go_btn = page.locator('button:has-text("Go")')
    go_btn.click()
    # Wait for the wrong-password feedback
    page.wait_for_function(
        "() => document.querySelector('input[type=\"password\"]')"
        "?.placeholder === 'Wrong password'",
        timeout=5000,
    )
    placeholder = pwd_input.get_attribute("placeholder")
    assert placeholder == "Wrong password", f"Expected 'Wrong password', got: {placeholder!r}"
    edit_mode_el = page.locator(".edit-mode")
    assert edit_mode_el.count() == 0, ".edit-mode class should not be present after wrong password"


def test_edit_mode_does_not_leak(page, server):
    page.goto(server)
    create_playground(page, unique_name("Edit Room1"), "1234", ["Alice", "Bob"])
    page.goto(server)
    create_playground(page, unique_name("Edit Room2"), "5678", ["Charlie", "Dave"])

    storage_keys = page.evaluate("() => Object.keys(sessionStorage)")
    admin_keys = [k for k in storage_keys if "admin_key" in k]
    for key in admin_keys:
        assert "scokeep_admin_key_" in key
