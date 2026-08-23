"""Shared UI test actions — create playgrounds, play rounds, etc.

Uses Playwright SYNC API to avoid event loop conflicts with pytest-asyncio.
"""

from playwright.sync_api import Page


def create_playground(page: Page, name: str, pin: str, players: list[str]):
    """Create a playground via the home screen form."""
    base = page.url.split("#")[0]
    page.goto(base)
    page.fill('input[placeholder*="name" i], input[name="name"]', name)
    page.fill('input[placeholder*="pin" i], input[type="password"]', pin)

    for player in players:
        player_input = page.locator(
            'input[placeholder*="player" i], input[placeholder*="name" i]'
        ).last
        player_input.fill(player)
        add_btn = page.locator('button:has-text("Add"), button:has-text("+")')
        if add_btn.count() > 0:
            add_btn.first.click()

    page.locator('button:has-text("Create")').click()
    page.wait_for_url("**/playground/**", timeout=5000)


def auth_playground(page: Page, server: str, name: str, pin: str):
    """Authenticate to an existing playground."""
    page.goto(server)
    page.fill('input[placeholder*="name" i], input[name="name"]', name)
    page.fill('input[placeholder*="pin" i], input[type="password"]', pin)
    page.locator('button:has-text("Enter"), button:has-text("Go")').click()
    page.wait_for_url("**/playground/**", timeout=5000)


def start_game(page: Page, settings: dict | None = None):
    """Click start game from lobby."""
    if settings:
        if "mode" in settings:
            mode_btn = page.locator(f'button:has-text("{settings["mode"]}")')
            if mode_btn.count() > 0:
                mode_btn.click()
        if "appearance" in settings:
            app_btn = page.locator(f'button:has-text("{settings["appearance"]}")')
            if app_btn.count() > 0:
                app_btn.click()

    page.locator('button:has-text("Start Game")').click()
    page.wait_for_selector(".keypad-grid", timeout=5000)


def enter_bid(page: Page, value: int):
    """Enter a bid via the keypad."""
    page.locator(f'.keypad-grid button:has-text("{value}")').click()
    confirm = page.locator('button:has-text("Confirm"), button:has-text("✓")')
    if confirm.count() > 0:
        confirm.first.click()


def enter_bids_for_all(page: Page, bids: list[int]):
    """Enter bids for all players in sequence."""
    for bid in bids:
        page.wait_for_selector(".keypad-grid", timeout=5000)
        enter_bid(page, bid)
    page.wait_for_timeout(500)


def confirm_bids(page: Page):
    """Confirm all bids and start the round."""
    start_btn = page.locator('button:has-text("Start Round")')
    if start_btn.count() > 0:
        start_btn.click()
        page.wait_for_timeout(500)


def enter_hands_won(page: Page, hands: list[int]):
    """Enter hands won for all players."""
    end_round_btn = page.locator('button:has-text("End Round"), button:has-text("Enter Results")')
    if end_round_btn.count() > 0:
        end_round_btn.first.click()
        page.wait_for_timeout(500)

    for hand in hands:
        page.wait_for_selector(".keypad-grid", timeout=5000)
        enter_bid(page, hand)
    page.wait_for_timeout(500)


def end_round(page: Page):
    """Finalize the round scoring."""
    done_btn = page.locator('button:has-text("Done"), button:has-text("End Round")')
    if done_btn.count() > 0:
        done_btn.first.click()
        page.wait_for_timeout(500)


def play_one_round(page: Page, bids: list[int], hands: list[int]):
    """Play a complete round: bid → confirm → play → hands → score."""
    enter_bids_for_all(page, bids)
    confirm_bids(page)
    enter_hands_won(page, hands)
    end_round(page)


def end_game(page: Page):
    """End the game from scoreboard or play screen."""
    end_btn = page.locator('button:has-text("End Game")')
    if end_btn.count() > 0:
        end_btn.click()
        confirm = page.locator('button:has-text("Confirm"), button:has-text("Yes")')
        if confirm.count() > 0:
            confirm.first.click()
        page.wait_for_timeout(1000)


VIEWPORTS = [
    {"width": 375, "height": 812, "name": "mobile"},
    {"width": 768, "height": 1024, "name": "tablet"},
    {"width": 1024, "height": 768, "name": "desktop"},
]
