"""Shared UI test actions — create playgrounds, play rounds, etc.

Uses Playwright SYNC API. Selectors match the actual HTML in screens/*.js.
"""

import uuid

from playwright.sync_api import Page


def unique_name(prefix: str) -> str:
    """Generate a unique playground name to avoid collisions across tests."""
    return f"{prefix} {uuid.uuid4().hex[:6]}"


def create_playground(page: Page, name: str, pin: str, players: list[str]):
    """Create a playground via the home screen form."""
    base = page.url.split("#")[0]
    page.goto(base)
    page.wait_for_selector("#create-form", timeout=5000)

    page.fill("#create-name", name)
    page.fill("#create-pin", pin)

    # Fill existing player inputs and add more if needed
    existing_inputs = page.locator(".player-name")
    for i, player in enumerate(players):
        if i < existing_inputs.count():
            existing_inputs.nth(i).fill(player)
        else:
            page.click("#add-player")
            page.locator(".player-name").last.fill(player)

    page.click('#create-form button[type="submit"]')
    page.wait_for_function("() => location.hash.includes('playground')", timeout=5000)


def auth_playground(page: Page, server: str, name: str, pin: str):
    """Authenticate to an existing playground via the Join tab."""
    page.goto(server)
    page.wait_for_selector(".tabs", timeout=5000)
    page.click('.tab[data-tab="join"]')
    page.wait_for_selector("#join-form:not(.hidden)", timeout=3000)
    page.fill("#join-name", name)
    page.fill("#join-pin", pin)
    page.click('#join-form button[type="submit"]')
    page.wait_for_function("() => location.hash.includes('playground')", timeout=5000)


def start_game(page: Page, settings: dict | None = None):
    """Click start game from lobby. Settings use <select> elements."""
    page.wait_for_selector("#start-game", timeout=5000)

    if settings:
        if "mode" in settings:
            page.select_option("#setting-mode", settings["mode"].lower())
        if "appearance" in settings:
            page.select_option("#setting-appearance", settings["appearance"].lower())
        if "sets" in settings:
            page.select_option("#setting-sets", str(settings["sets"]))

    page.click("#start-game")
    page.wait_for_selector(".keypad", timeout=30000)


def enter_bid(page: Page, value: int):
    """Enter a bid via the keypad and wait for advance."""
    # Capture current player name so we can detect screen advance
    name_el = page.locator(".bid-player-name")
    old_name = name_el.text_content() if name_el.count() > 0 else ""
    page.locator(f".keypad-key:has-text('{value}')").click()
    # Wait until player name changes (next player) or disappears (confirm)
    escaped = old_name.replace("'", "\\'")
    page.wait_for_function(
        "() => {"
        "  const el = document.querySelector('.bid-player-name');"
        f"  return !el || el.textContent !== '{escaped}';"
        "}",
        timeout=10000,
    )


def enter_bids_for_all(page: Page, bids: list[int]):
    """Enter bids for all players in sequence."""
    for bid in bids:
        page.wait_for_selector(".keypad", timeout=30000)
        enter_bid(page, bid)


def confirm_bids(page: Page):
    """Confirm all bids and start the round."""
    start_btn = page.locator('button:has-text("Start Round")')
    if start_btn.count() > 0:
        start_btn.click()
        page.wait_for_function("() => location.hash.includes('play')", timeout=10000)


def enter_hands_won(page: Page, hands: list[int]):
    """Enter hands won for all players after clicking enter round end."""
    end_round_btn = page.locator('button:has-text("End Round"), button:has-text("Enter Results")')
    if end_round_btn.count() > 0:
        end_round_btn.first.click()
        page.wait_for_function("() => location.hash.includes('roundend')", timeout=10000)

    for hand in hands:
        page.wait_for_selector(".keypad", timeout=30000)
        enter_bid(page, hand)


def end_round(page: Page):
    """Finalize the round scoring."""
    selectors = (
        'button:has-text("Score Round"), button:has-text("Done"), button:has-text("End Round")'
    )
    done_btn = page.locator(selectors)
    if done_btn.count() > 0:
        done_btn.first.click()
        page.wait_for_function("() => location.hash.includes('scoreboard')", timeout=10000)


def play_one_round(page: Page, bids: list[int], hands: list[int]):
    """Play a complete round: bid → confirm → play → hands → score."""
    enter_bids_for_all(page, bids)
    confirm_bids(page)
    enter_hands_won(page, hands)
    end_round(page)


def end_game(page: Page):
    """End the game from scoreboard or play screen."""
    end_btn = page.locator('#end-game, #end-game-btn, button:has-text("End Game")')
    if end_btn.count() > 0:
        # Accept browser confirm() dialog before triggering it
        page.once("dialog", lambda dialog: dialog.accept())
        end_btn.first.click()
        page.wait_for_function(
            "() => location.hash.includes('scoreboard') || location.hash.includes('final')",
            timeout=10000,
        )


def navigate_to_stats(page: Page, server: str, name: str, pin: str):
    """Auth to a playground and click Stats."""
    auth_playground(page, server, name, pin)
    page.wait_for_selector("#view-stats", timeout=5000)
    page.click("#view-stats")
    page.wait_for_timeout(1000)


VIEWPORTS = [
    {"width": 375, "height": 812, "name": "mobile"},
    {"width": 768, "height": 1024, "name": "tablet"},
    {"width": 1024, "height": 768, "name": "desktop"},
]
