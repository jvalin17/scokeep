"""Scoresheet IDB/sync Playwright — SS-UI-10."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

from tests.ui.helpers import create_playground, unique_name
from tests.ui.scoresheet_helpers import (
    enter_scores_for_all,
    press_digit,
    score_round,
    start_scoresheet,
)

pytestmark = [pytest.mark.scoresheet]


class TestScoresheetIdb:
    def test_ss_ui_10_offline_play_sync_after_lock(self, page: Page, server: str):
        """MG-MUST-10: no sync-round on keypress; sync after Score Round when online."""
        page.goto(server)
        sync_calls: list[str] = []

        def track_sync(route):
            sync_calls.append(route.request.url)
            route.continue_()

        page.route("**/api/game/*/sync-round", track_sync)

        create_playground(page, unique_name("SS IDB"), "4242", ["Maria", "Diego"])
        start_scoresheet(page)

        # Digits must not trigger sync-round
        press_digit(page, 3)
        press_digit(page, 0)
        page.wait_for_timeout(200)
        assert sync_calls == [], f"sync on keypress: {sync_calls}"

        # Finish round with sync allowed
        page.unroute("**/api/game/*/sync-round")
        page.route("**/api/game/*/sync-round", track_sync)
        # Need to re-enter from empty? display still has 30 — clear and enter both
        # Clear buffer via long-press backspace (no dedicated C key)
        page.locator("[data-dialer-backspace]").dispatch_event("pointerdown")
        page.wait_for_timeout(500)
        page.locator("[data-dialer-backspace]").dispatch_event("pointerup")
        enter_scores_for_all(page, [30, 10])
        score_round(page)
        page.wait_for_timeout(800)
        assert any("sync-round" in url for url in sync_calls), (
            f"expected sync after lock, got {sync_calls}"
        )
