"""Judgement regression smoke — SS-UI-11 / MG regression gate.

Must stay green on feature/multi-game. Never skip.
"""

from __future__ import annotations

import pytest

from tests.ui.helpers import (
    create_playground,
    enter_bids_for_all,
    enter_hands_won,
    start_game,
    unique_name,
)

pytestmark = pytest.mark.judgement_smoke


@pytest.fixture
def judgement_started(page, server):
    page.goto(server)
    create_playground(page, unique_name("JudgementSmoke"), "1234", ["Alice", "Bob", "Charlie"])
    start_game(page, {"mode": "Expert"})
    return page


def test_judgement_one_round_smoke(judgement_started):
    """SS-UI-11: bid → confirm → hands → scoreboard/roundend still works."""
    page = judgement_started
    page.wait_for_selector(".keypad", timeout=60000)
    enter_bids_for_all(page, [2, 3, 1])
    start_btn = page.locator('button:has-text("Start Round")')
    start_btn.wait_for(state="visible", timeout=60000)
    start_btn.click()
    page.wait_for_function("() => location.hash.includes('play')", timeout=10000)
    enter_hands_won(page, [2, 3, 3])
    page.wait_for_function(
        "() => location.hash.includes('roundend') || location.hash.includes('scoreboard')",
        timeout=10000,
    )
    url_hash = page.evaluate("() => location.hash")
    assert "roundend" in url_hash or "scoreboard" in url_hash
