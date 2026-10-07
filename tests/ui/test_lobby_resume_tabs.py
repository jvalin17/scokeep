"""Lobby Resume Game appears only on the matching game-type tab."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.ui.helpers import create_playground, unique_name
from tests.ui.scoresheet_helpers import start_scoresheet

pytestmark = [pytest.mark.scoresheet]


class TestLobbyResumeByTab:
    def test_resume_shows_on_scoresheet_tab_only(self, page: Page, server: str):
        page.goto(server)
        create_playground(page, unique_name("Resume Tab"), "4242", ["Maria", "Diego"])
        start_scoresheet(page)
        page.locator('[aria-label="Back to room"]').click()
        page.wait_for_selector("#start-game", timeout=15000)

        expect(page.locator("#resume-game")).to_be_visible()
        expect(page.locator('[data-game-tab="scoresheet"]')).to_have_attribute(
            "aria-selected", "true"
        )

        page.locator('[data-game-tab="kachuful"]').click()
        expect(page.locator("#resume-game")).to_have_count(0)

        page.locator('[data-game-tab="scoresheet"]').click()
        expect(page.locator("#resume-game")).to_be_visible()
