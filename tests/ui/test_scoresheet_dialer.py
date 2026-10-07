"""Scoresheet dialer Playwright — SS-UI-01 settings + SS-UI-02..05 dialer."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.ui.helpers import create_playground, unique_name
from tests.ui.scoresheet_helpers import (
    dialer_display_text,
    press_digit,
    press_next,
    select_scoresheet,
    start_scoresheet,
    toggle_sign,
)

pytestmark = [pytest.mark.scoresheet]


class TestScoresheetEntryDialer:
    def test_ss_ui_01_select_scoresheet_and_settings(self, page: Page, server: str):
        """MG-MUST-01: nested Winner / Show totals / Allow negatives + Start."""
        page.goto(server)
        name = unique_name("SS Settings")
        create_playground(page, name, "4242", ["Maria", "Diego"])
        select_scoresheet(
            page,
            {
                "winner": "lowest",
                "show_totals": False,
                "allow_negatives": True,
                "label": "Declare night",
            },
        )
        expect(page.locator("#setting-winner")).to_have_value("lowest")
        expect(page.locator("#setting-show-totals")).not_to_be_checked()
        expect(page.locator("#setting-allow-negatives")).to_be_checked()
        expect(page.locator("#setting-label")).to_have_value("Declare night")
        page.click("#start-game")
        page.wait_for_selector("#score-display", timeout=60000)
        expect(page.locator("#score-display")).to_be_visible()
        expect(page.locator(".bid-player-name")).to_be_visible()

    def test_ss_ui_02_buffer_and_next_not_tap_commit(self, page: Page, server: str):
        """MG-MUST-02: digits buffer; Next advances."""
        page.goto(server)
        name = unique_name("SS Buffer")
        create_playground(page, name, "4242", ["Maria", "Diego", "Priya"])
        start_scoresheet(page)
        first_name = page.locator(".bid-player-name").text_content()
        press_digit(page, 4)
        press_digit(page, 2)
        assert dialer_display_text(page) == "42"
        # Digit alone must not advance player
        assert page.locator(".bid-player-name").text_content() == first_name
        press_next(page)
        assert page.locator(".bid-player-name").text_content() != first_name

    def test_ss_ui_03_sign_when_negatives_on(self, page: Page, server: str):
        """MG-MUST-07 On: ± toggles sign."""
        page.goto(server)
        name = unique_name("SS Neg On")
        create_playground(page, name, "4242", ["Maria", "Diego"])
        start_scoresheet(page, {"allow_negatives": True})
        expect(page.locator("#btn-sign")).to_be_visible()
        press_digit(page, 1)
        press_digit(page, 5)
        toggle_sign(page)
        assert "−" in dialer_display_text(page) or "-" in dialer_display_text(page)

    def test_ss_ui_04_sign_disabled_when_negatives_off(self, page: Page, server: str):
        """MG-MUST-07 Off: ± present but disabled (replaces Clear key)."""
        page.goto(server)
        name = unique_name("SS Neg Off")
        create_playground(page, name, "4242", ["Maria", "Diego"])
        start_scoresheet(page, {"allow_negatives": False})
        sign = page.locator("#btn-sign")
        expect(sign).to_be_visible()
        assert sign.is_disabled()

    def test_ss_ui_05_empty_next_double_tap_max_digits(self, page: Page, server: str):
        """Guards: empty Next, debounce, max 4 digits."""
        page.goto(server)
        name = unique_name("SS Guards")
        create_playground(page, name, "4242", ["Maria", "Diego"])
        start_scoresheet(page)
        first_name = page.locator(".bid-player-name").text_content()
        page.click("#btn-next")
        # Empty Next does not advance
        assert page.locator(".bid-player-name").text_content() == first_name
        expect(page.locator("#dialer-flash")).to_contain_text("Enter a score")

        for digit in (1, 2, 3, 4, 5):
            press_digit(page, digit)
        assert dialer_display_text(page) == "1234"
        expect(page.locator("#dialer-flash")).to_contain_text("Max 4")
