"""Responsive rendering tests — all screens at 3 viewports."""

import pytest

from tests.ui.helpers import (
    VIEWPORTS,
    create_playground,
    start_game,
)


@pytest.fixture
def game_page(page, server):
    page.goto(server)
    create_playground(page, "UITest Responsive", "1234", ["Alice", "Bob", "Charlie"])
    return page


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=lambda v: v["name"])
def test_lobby_responsive(game_page, viewport):
    game_page.set_viewport_size(viewport)
    overflow = game_page.evaluate(
        "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )
    assert not overflow


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=lambda v: v["name"])
def test_bidding_responsive(game_page, viewport):
    game_page.set_viewport_size(viewport)
    start_game(game_page)
    overflow = game_page.evaluate(
        "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )
    assert not overflow
    keypad = game_page.locator(".keypad-grid")
    assert keypad.is_visible()


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=lambda v: v["name"])
def test_desktop_standard_has_card(page, server, viewport):
    if viewport["width"] < 900:
        pytest.skip("Card styling only on desktop")
    page.set_viewport_size(viewport)
    page.goto(server)
    app_el = page.locator("#app")
    shadow = app_el.evaluate("el => getComputedStyle(el).boxShadow")
    assert shadow != "none"


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=lambda v: v["name"])
def test_desktop_interactive_preserves_colors(page, server, viewport):
    if viewport["width"] < 900:
        pytest.skip("Only relevant on desktop")
    page.set_viewport_size(viewport)
    page.goto(server)
    create_playground(page, f"UITest Color {viewport['name']}", "1234", ["A", "B", "C"])
    start_game(page, {"appearance": "Interactive"})

    appearance = page.locator("body").get_attribute("data-appearance")
    if appearance == "interactive":
        body_bg = page.evaluate("() => getComputedStyle(document.body).backgroundColor")
        assert body_bg != "rgb(238, 238, 238)"
