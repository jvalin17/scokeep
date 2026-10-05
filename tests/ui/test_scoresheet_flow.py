"""Scoresheet Playwright flows — SS-UI-06 lock + SS-UI-07/09 board loop."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.ui.helpers import create_playground, unique_name
from tests.ui.scoresheet_helpers import (
    assert_standings_visible,
    enter_scores_for_all,
    score_round,
    start_scoresheet,
    undo_last_round,
)

pytestmark = [pytest.mark.scoresheet]


class TestScoresheetRoundLock:
    def test_ss_ui_06_round_review_edit_and_lock(self, page: Page, server: str):
        """MG-MUST-03: review strip Edit + Score Round → scoreboard."""
        page.goto(server)
        create_playground(page, unique_name("SS Lock"), "4242", ["Maria", "Diego"])
        start_scoresheet(page)
        enter_scores_for_all(page, [12, 8])
        expect(page.locator("#scoresheet-review")).to_be_visible()
        page.locator('#scoresheet-review button:has-text("Edit")').first.click()
        expect(page.locator("#score-display")).to_be_visible()
        enter_scores_for_all(page, [12, 8])
        expect(page.locator("#scoresheet-review")).to_be_visible()
        score_round(page)
        expect(page.locator("#scoreboard-standings, [data-standings]")).to_be_visible()


class TestScoresheetBoardLoop:
    def test_ss_ui_07_show_totals_on_vs_off(self, page: Page, server: str):
        """MG-MUST-04/05: standings vs hidden intermission."""
        page.goto(server)
        create_playground(page, unique_name("SS Totals"), "4242", ["Maria", "Diego"])
        start_scoresheet(page, {"show_totals": True})
        enter_scores_for_all(page, [5, 3])
        score_round(page)
        assert_standings_visible(page, True)

        page.goto(server)
        create_playground(page, unique_name("SS Hidden"), "4242", ["Maria", "Diego"])
        start_scoresheet(page, {"show_totals": False})
        enter_scores_for_all(page, [5, 3])
        score_round(page)
        expect(page.locator("[data-intermission]")).to_be_visible()
        assert_standings_visible(page, False)

    def test_ss_ui_09_undo_and_edit_completed_round(self, page: Page, server: str):
        """MG-MUST-08/09: Undo Last Round + Edit Round + Next Round."""
        page.goto(server)
        create_playground(page, unique_name("SS Undo"), "4242", ["Maria", "Diego"])
        start_scoresheet(page)
        enter_scores_for_all(page, [20, 10])
        score_round(page)
        expect(page.locator("#next-round")).to_be_visible()
        expect(page.locator("#end-game")).to_have_text("Finished")

        undo_last_round(page)
        page.wait_for_selector("#score-display", timeout=15000)
        enter_scores_for_all(page, [1, 2])
        score_round(page)

        page.click("#edit-round")
        page.wait_for_selector("#score-display", timeout=15000)
        enter_scores_for_all(page, [9, 4])
        score_round(page)

        page.click("#next-round")
        page.wait_for_selector("#score-display", timeout=15000)
        expect(page.locator(".bid-player-name")).to_be_visible()


class TestScoresheetFlowDeferred:
    pass
