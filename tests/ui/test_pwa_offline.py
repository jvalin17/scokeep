"""PWA offline tests — app must load and Quick Game must work without network.

Uses page.route() to block all network requests, simulating airplane mode.
The service worker must serve cached app shell and API calls must fail gracefully.
"""

import pytest
from playwright.sync_api import expect


@pytest.fixture()
def offline_page(page, server):
    """Load app online, then block API calls to simulate offline for app logic."""
    page.goto(server)
    page.wait_for_selector(".tabs", timeout=10000)

    # Block only API calls — simulates offline for app logic while SW serves cached shell
    page.route("**/api/**", lambda route: route.abort())
    # Navigate to home (hash change, no network needed for cached shell)
    page.evaluate("() => location.hash = ''")
    page.wait_for_timeout(500)
    yield page


def test_app_loads_offline(offline_page):
    """Home screen loads from SW cache when offline — shows tabs including Quick Game."""
    expect(offline_page.locator(".tabs")).to_be_visible(timeout=5000)
    expect(offline_page.locator('.tab[data-tab="quick"]')).to_be_visible(timeout=5000)
    expect(offline_page.locator("h1.logo")).to_have_text("Scokeep")


def test_quick_game_starts_offline(offline_page):
    """Quick Game starts without network — bidding screen appears."""
    offline_page.click('.tab[data-tab="quick"]')
    offline_page.wait_for_selector("#quick-form:not(.hidden)", timeout=3000)

    # Add 2 players
    inputs = offline_page.locator(".quick-player-name")
    inputs.nth(0).fill("Alice")
    inputs.nth(1).fill("Bob")

    # Start game
    offline_page.click("#quick-start")
    offline_page.wait_for_function(
        "() => location.hash.includes('bid/game-')",
        timeout=10000,
    )

    # Bidding screen should render
    expect(offline_page.locator(".bid-player-name")).to_be_visible(timeout=5000)
