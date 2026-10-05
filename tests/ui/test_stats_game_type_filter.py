"""Stats screen filters history by Judgement / Scoresheet / All."""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

from tests.ui.helpers import (
    auth_playground,
    create_playground,
    end_game,
    navigate_to_stats,
    play_one_round,
    start_game,
    unique_name,
)
from tests.ui.scoresheet_helpers import enter_scores_for_all, score_round, start_scoresheet

pytestmark = [pytest.mark.scoresheet]


class TestStatsGameTypeFilter:
    def test_stats_filter_tabs_isolate_history(self, page: Page, server: str):
        room = unique_name("Stats Filter UI")
        page.goto(server)
        create_playground(page, room, "4242", ["Maria", "Diego"])

        # Scoresheet game
        start_scoresheet(page, {"label": "Declare night"})
        enter_scores_for_all(page, [15, 5])
        score_round(page)
        page.click("#end-game")
        page.wait_for_selector("#confirm-final", timeout=15000)
        page.click("#confirm-final")
        page.wait_for_function("() => location.hash.includes('scoreboard')", timeout=15000)

        # Re-auth to lobby for Judgement game
        auth_playground(page, server, room, "4242")
        page.wait_for_selector("#start-game", timeout=15000)
        page.locator('[data-game-tab="kachuful"]').click()
        start_game(page, {"sets": 1})
        play_one_round(page, [2, 3], [2, 6])
        end_game(page)

        navigate_to_stats(page, server, room, "4242")
        page.wait_for_selector("[data-game-type-filter]", timeout=15000)

        page.locator('[data-game-type-filter="all"]').click()
        expect(page.locator('[data-game-type-filter="all"]')).to_have_attribute(
            "aria-selected", "true"
        )
        page.locator('.stats-tab[data-tab="history"]').click()
        expect(page.locator(".stats-game-card")).to_have_count(2, timeout=15000)

        page.locator('[data-game-type-filter="scoresheet"]').click()
        expect(page.locator('[data-game-type-filter="scoresheet"]')).to_have_attribute(
            "aria-selected", "true"
        )
        page.locator('.stats-tab[data-tab="history"]').click()
        expect(page.locator(".stats-game-card")).to_have_count(1, timeout=15000)
        expect(page.locator(".stats-mode")).to_contain_text("Declare")
        expect(page).to_have_url(re.compile(r"stats/.+/scoresheet"))

        page.locator('[data-game-type-filter="kachuful"]').click()
        expect(page.locator('[data-game-type-filter="kachuful"]')).to_have_attribute(
            "aria-selected", "true"
        )
        page.locator('.stats-tab[data-tab="history"]').click()
        expect(page.locator(".stats-game-card")).to_have_count(1, timeout=15000)
