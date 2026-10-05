"""Scoresheet happy-path E2E — lobby → dialer → lock → Next → Finished."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.ui.helpers import create_playground, unique_name
from tests.ui.scoresheet_helpers import (
    enter_scores_for_all,
    score_round,
    start_scoresheet,
)

pytestmark = [pytest.mark.scoresheet]


def test_ss_e2e_01_scoresheet_happy_path(page: Page, server: str):
    """Lobby → entry → review → lock → Next → second round → Finished."""
    page.goto(server)
    create_playground(page, unique_name("SS E2E"), "4242", ["Maria", "Diego", "Priya"])
    start_scoresheet(
        page,
        {"winner": "highest", "show_totals": True, "label": "Declare"},
    )
    enter_scores_for_all(page, [10, 20, 15])
    score_round(page)
    expect(page.locator("[data-standings]")).to_be_visible()

    page.click("#next-round")
    page.wait_for_selector("#score-display", timeout=15000)
    enter_scores_for_all(page, [5, 5, 5])
    score_round(page)

    page.click("#end-game")
    page.wait_for_selector("#confirm-final", timeout=15000)
    page.click("#confirm-final")
    page.wait_for_selector(".final-winner", timeout=15000)
    # Entry order after dealer: Diego, Priya, Maria → totals 15 / 25 / 20
    expect(page.locator(".final-winner")).to_contain_text("Priya")
