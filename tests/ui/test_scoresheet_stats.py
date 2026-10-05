"""Scoresheet finished ranking + stats awards gate — SS-UI-08 / SS-UI-12."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.ui.helpers import create_playground, navigate_to_stats, unique_name
from tests.ui.scoresheet_helpers import (
    enter_scores_for_all,
    score_round,
    start_scoresheet,
)

pytestmark = [pytest.mark.scoresheet]


class TestScoresheetFinished:
    def test_ss_ui_08_winner_high_vs_low(self, page: Page, server: str):
        """MG-MUST-06: lowest-wins ranking on Finished."""
        page.goto(server)
        create_playground(page, unique_name("SS Rank"), "4242", ["Maria", "Diego"])
        start_scoresheet(page, {"winner": "lowest"})
        # Entry order after dealer 0: Diego then Maria
        enter_scores_for_all(page, [5, 30])
        score_round(page)
        page.click("#end-game")
        page.wait_for_selector("#confirm-final, .review-screen", timeout=15000)
        if page.locator("#confirm-final").count():
            page.click("#confirm-final")
        page.wait_for_selector(".final-winner", timeout=15000)
        expect(page.locator(".final-winner")).to_contain_text("Diego")


class TestScoresheetStats:
    def test_ss_ui_12_judgement_awards_not_on_scoresheet(self, page: Page, server: str):
        """MG-MUST-12: Scoresheet-only room has no Judgement last-game titles."""
        page.goto(server)
        room_name = unique_name("SS StatsGate")
        create_playground(page, room_name, "4242", ["Maria", "Diego"])
        start_scoresheet(page)
        enter_scores_for_all(page, [4, 6])
        score_round(page)
        page.click("#end-game")
        page.wait_for_selector("#confirm-final", timeout=15000)
        page.click("#confirm-final")
        page.wait_for_function(
            "() => location.hash.includes('scoreboard')",
            timeout=15000,
        )
        navigate_to_stats(page, server, room_name, "4242")
        page.wait_for_selector(".stats-tab", timeout=10000)
        page.click('.stats-tab[data-tab="highlights"]')
        page.wait_for_timeout(400)
        assert page.locator(".awards-card-title:has-text('Sniper')").count() == 0
        assert page.locator("text=Bid exactly 1").count() == 0
