"""Edit mode + clear stats tests — action sheet dialog flow."""

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


def test_gear_opens_action_dialog(stats_with_game):
    """Clicking gear opens the action sheet dialog overlay."""
    page = stats_with_game
    gear_btn = page.locator("#stats-gear")
    gear_btn.wait_for(state="visible", timeout=5000)
    gear_btn.click()
    dialog = page.locator(".action-dialog")
    dialog.wait_for(state="visible", timeout=3000)
    assert dialog.is_visible(), "Action dialog should be visible"


def test_dialog_has_edit_and_clear_buttons(stats_with_game):
    """Dialog shows Edit Mode and Clear All Stats buttons."""
    page = stats_with_game
    page.click("#stats-gear")
    page.wait_for_selector(".action-dialog", timeout=3000)
    edit_btn = page.locator("#toggle-edit")
    clear_btn = page.locator("#clear-stats")
    assert edit_btn.is_visible(), "Edit Mode button should be in dialog"
    assert clear_btn.is_visible(), "Clear All Stats button should be in dialog"


def test_dialog_closes_on_overlay_click(stats_with_game):
    """Clicking the overlay backdrop dismisses the dialog."""
    page = stats_with_game
    page.click("#stats-gear")
    page.wait_for_selector(".action-dialog", timeout=3000)
    # Click the overlay (outside the dialog content)
    page.locator(".action-overlay").click(position={"x": 10, "y": 10})
    page.wait_for_timeout(300)
    assert page.locator(".action-overlay").is_hidden(), "Overlay should be hidden"


def test_dialog_closes_on_x_button(stats_with_game):
    """Clicking × dismisses the dialog."""
    page = stats_with_game
    page.click("#stats-gear")
    page.wait_for_selector(".action-dialog", timeout=3000)
    page.click(".action-dialog-close")
    page.wait_for_timeout(300)
    assert page.locator(".action-overlay").is_hidden()


def test_edit_mode_toggle(stats_with_game):
    """Correct admin password enables edit mode with orange background."""
    page = stats_with_game
    page.click("#stats-gear")
    page.wait_for_selector(".action-dialog", timeout=3000)
    page.click("#toggle-edit")
    page.wait_for_selector('input[type="password"]', timeout=3000)
    page.fill('input[type="password"]', "test-admin-key")
    page.click('button:has-text("Go")')
    page.wait_for_timeout(500)
    edit_mode = page.locator(".edit-mode")
    assert edit_mode.count() > 0, ".edit-mode class should be present"


def test_edit_mode_scores_visible(stats_with_game):
    """BUG: color:#fff on edit-mode made scores invisible on white cards.
    Scores inside .stats-content must remain dark text in edit mode."""
    page = stats_with_game
    # Enter edit mode
    page.click("#stats-gear")
    page.wait_for_selector(".action-dialog", timeout=3000)
    page.click("#toggle-edit")
    page.wait_for_selector('input[type="password"]', timeout=3000)
    page.fill('input[type="password"]', "test-admin-key")
    page.click('button:has-text("Go")')
    page.wait_for_timeout(500)
    assert page.locator(".edit-mode").count() > 0

    # Switch to Games tab to see scoresheets
    games_tab = page.locator('.stats-tab:has-text("Games")')
    if games_tab.count() > 0:
        games_tab.click()
        page.wait_for_timeout(500)

    # Stats content card must have non-white background (readable)
    content_bg = page.locator(".stats-content").evaluate(
        "el => getComputedStyle(el).backgroundColor"
    )
    assert content_bg != "rgba(0, 0, 0, 0)", "stats-content must have a background in edit mode"

    # Text inside stats-content must NOT be white
    content_color = page.locator(".stats-content").evaluate("el => getComputedStyle(el).color")
    assert content_color != "rgb(255, 255, 255)", (
        f"Text in stats-content must not be white in edit mode, got: {content_color}"
    )


def test_edit_mode_wrong_password(stats_with_game):
    """Wrong admin password shows 'Wrong password', no edit mode."""
    page = stats_with_game
    page.click("#stats-gear")
    page.wait_for_selector(".action-dialog", timeout=3000)
    page.click("#toggle-edit")
    page.wait_for_selector('input[type="password"]', timeout=3000)
    page.fill('input[type="password"]', "definitely-wrong")
    page.click('button:has-text("Go")')
    page.wait_for_function(
        "() => document.querySelector('input[type=\"password\"]')"
        "?.placeholder === 'Wrong password'",
        timeout=5000,
    )
    edit_mode = page.locator(".edit-mode")
    assert edit_mode.count() == 0, "No edit-mode after wrong password"


def test_exit_edit_mode_via_gear(stats_with_game):
    """When edit mode is ON, gear dialog shows 'Exit Edit Mode'."""
    page = stats_with_game
    # Enter edit mode
    page.click("#stats-gear")
    page.wait_for_selector(".action-dialog", timeout=3000)
    page.click("#toggle-edit")
    page.wait_for_selector('input[type="password"]', timeout=3000)
    page.fill('input[type="password"]', "test-admin-key")
    page.click('button:has-text("Go")')
    page.wait_for_timeout(500)
    assert page.locator(".edit-mode").count() > 0

    # Click gear again — should show "Exit Edit Mode"
    page.click("#stats-gear")
    page.wait_for_selector(".action-dialog", timeout=3000)
    exit_btn = page.locator("#toggle-edit")
    assert "Exit" in exit_btn.inner_text(), "Button should say Exit Edit Mode"
    exit_btn.click()
    page.wait_for_timeout(500)
    assert page.locator(".edit-mode").count() == 0, "Edit mode should be off"


def test_clear_stats_requires_delete_confirmation(stats_with_game):
    """Clear stats shows warning and requires typing DELETE."""
    page = stats_with_game
    page.click("#stats-gear")
    page.wait_for_selector(".action-dialog", timeout=3000)
    page.click("#clear-stats")
    # Warning should appear
    warning = page.locator(".clear-warning")
    warning.wait_for(state="visible", timeout=3000)
    assert "cannot be recovered" in warning.inner_text().lower()
    # Proceed button should be disabled
    proceed_btn = page.locator("#clear-proceed")
    assert proceed_btn.is_disabled(), "Proceed should be disabled before typing DELETE"
    # Type DELETE
    page.fill("#clear-confirm-input", "DELETE")
    page.wait_for_timeout(200)
    assert not proceed_btn.is_disabled(), "Proceed should be enabled after typing DELETE"


def test_clear_stats_cancel(stats_with_game):
    """Cancel button dismisses the clear warning."""
    page = stats_with_game
    page.click("#stats-gear")
    page.wait_for_selector(".action-dialog", timeout=3000)
    page.click("#clear-stats")
    page.wait_for_selector(".clear-warning", timeout=3000)
    page.click("#clear-cancel")
    page.wait_for_timeout(300)
    assert page.locator(".clear-warning").is_hidden(), "Warning should be hidden after cancel"


def test_edit_mode_does_not_leak(page, server):
    page.goto(server)
    create_playground(page, unique_name("Edit Room1"), "1234", ["Alice", "Bob"])
    page.goto(server)
    create_playground(page, unique_name("Edit Room2"), "5678", ["Charlie", "Dave"])
    storage_keys = page.evaluate("() => Object.keys(sessionStorage)")
    admin_keys = [k for k in storage_keys if "admin_key" in k]
    for key in admin_keys:
        assert "scokeep_admin_key_" in key
