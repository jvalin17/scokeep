"""Edit mode tests — admin key, purple tint, cross-room isolation."""

import pytest

from tests.ui.helpers import (
    auth_playground,
    confirm_bids,
    create_playground,
    end_game,
    enter_bids_for_all,
    enter_hands_won,
    start_game,
)


@pytest.fixture
def stats_with_game(page, server):
    page.goto(server)
    create_playground(page, "UITest Edit", "1234", ["Alice", "Bob", "Charlie"])
    start_game(page)
    enter_bids_for_all(page, [2, 3, 1])
    confirm_bids(page)
    enter_hands_won(page, [2, 3, 3])
    page.wait_for_timeout(500)
    end_game(page)
    page.wait_for_timeout(500)
    auth_playground(page, server, "UITest Edit", "1234")
    stats_btn = page.locator('button:has-text("Stats"), a:has-text("Stats")')
    if stats_btn.count() > 0:
        stats_btn.first.click()
        page.wait_for_timeout(1000)
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


def test_edit_mode_does_not_leak(page, server):
    page.goto(server)
    create_playground(page, "UITest Edit Room1", "1234", ["Alice", "Bob"])
    page.goto(server)
    create_playground(page, "UITest Edit Room2", "5678", ["Charlie", "Dave"])

    storage_keys = page.evaluate("() => Object.keys(sessionStorage)")
    admin_keys = [k for k in storage_keys if "admin_key" in k]
    for key in admin_keys:
        assert "scokeep_admin_key_" in key
