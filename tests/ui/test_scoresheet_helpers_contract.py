"""Contract: Scoresheet Playwright helpers export the QA-agreed API.

Does not require Scoresheet UI — only import surface for SS-UI suite.
"""

import tests.ui.scoresheet_helpers as helpers

REQUIRED = [
    "SEL_GAME_SCORESHEET",
    "SEL_DIALER_DISPLAY",
    "SEL_NEXT",
    "SEL_SIGN",
    "SEL_SCORE_ROUND",
    "SEL_UNDO_LAST",
    "select_scoresheet",
    "start_scoresheet",
    "press_digit",
    "press_next",
    "enter_score",
    "enter_scores_for_all",
    "score_round",
    "assert_standings_visible",
    "undo_last_round",
    "block_game_sync_routes",
]


def test_scoresheet_helper_exports():
    for name in REQUIRED:
        assert hasattr(helpers, name), f"missing scoresheet helper: {name}"
