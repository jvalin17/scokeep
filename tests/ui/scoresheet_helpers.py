"""Scoresheet Playwright helpers — buffer + Next (not Judgement tap-commit).

Selectors match lobby Type select + entry dialer DOM.
Do NOT call tests.ui.helpers.enter_bid from Scoresheet flows.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

# Lobby: Game type tabs (Judgement | Scoresheet)
SEL_GAME_TYPE = '.lobby-game-tabs, [role="tablist"][aria-label="Game type"]'
SEL_GAME_SCORESHEET = '[data-game-tab="scoresheet"]'
SEL_DIALER_DISPLAY = "#score-display, .score-display, [data-dialer-display]"
SEL_NEXT = '#btn-next, button:has-text("Next")'
SEL_SIGN = '#btn-sign, [data-dialer-sign]'
SEL_BACKSPACE = "[data-dialer-backspace]"
SEL_REVIEW = "#scoresheet-review, .scoresheet-review, [data-scoresheet-review]"
SEL_SCORE_ROUND = 'button:has-text("Score Round"), #btn-score-round'
SEL_UNDO_LAST = 'button:has-text("Undo Last Round"), #undo-last-round'
SEL_EDIT_ROUND = 'button:has-text("Edit Round"), #edit-round'
SEL_STANDINGS = ".scoreboard-standings, #scoreboard-standings, [data-standings]"
SEL_SETTING_WINNER = "#setting-winner"
SEL_SETTING_SHOW_TOTALS = "#setting-show-totals"
SEL_SETTING_NEGATIVES = "#setting-allow-negatives"
SEL_SETTING_LABEL = "#setting-label"
SEL_START = "#start-game"


def scoresheet_ui_present(page: Page) -> bool:
    """True when lobby exposes the Scoresheet game tab."""
    return page.locator(SEL_GAME_SCORESHEET).count() > 0


def select_scoresheet(page: Page, settings: dict | None = None) -> None:
    """Lobby: choose Scoresheet tab and apply nested settings."""
    page.wait_for_selector(SEL_GAME_SCORESHEET, timeout=10000)
    page.locator(SEL_GAME_SCORESHEET).click()
    page.wait_for_selector(SEL_SETTING_WINNER, timeout=5000)
    if not settings:
        return
    if "winner" in settings:
        page.select_option(SEL_SETTING_WINNER, settings["winner"])
    if "show_totals" in settings:
        want_on = settings["show_totals"] in (True, "on", "On", "true", "1")
        checkbox = page.locator(SEL_SETTING_SHOW_TOTALS)
        if checkbox.is_checked() != want_on:
            checkbox.click()
    if "allow_negatives" in settings:
        want_on = settings["allow_negatives"] in (True, "on", "On", "true", "1")
        checkbox = page.locator(SEL_SETTING_NEGATIVES)
        if checkbox.is_checked() != want_on:
            checkbox.click()
    if "label" in settings:
        page.fill(SEL_SETTING_LABEL, settings["label"])


def start_scoresheet(page: Page, settings: dict | None = None) -> None:
    """Select Scoresheet, Start, wait for dialer (not Judgement bid auto-advance)."""
    select_scoresheet(page, settings)
    page.locator(SEL_START).first.click()
    page.wait_for_selector(SEL_DIALER_DISPLAY, timeout=60000)


def dialer_display_text(page: Page) -> str:
    el = page.locator(SEL_DIALER_DISPLAY).first
    el.wait_for(state="visible", timeout=10000)
    return (el.text_content() or "").strip()


def press_digit(page: Page, digit: int) -> None:
    """Click a keypad digit — exact text match (no network wait)."""
    page.evaluate(
        """(expected) => {
            const match = [...document.querySelectorAll('.keypad-key')]
              .find((el) => (el.textContent || '').trim() === String(expected));
            if (!match) throw new Error('digit key not found: ' + expected);
            match.click();
        }""",
        digit,
    )


def press_backspace(page: Page) -> None:
    page.locator(SEL_BACKSPACE).first.click()


def toggle_sign(page: Page) -> None:
    sign = page.locator(SEL_SIGN)
    if sign.count() == 0:
        raise AssertionError("± control missing (Allow negatives should be On)")
    sign.first.click()


def press_next(page: Page) -> None:
    """Commit buffer; wait for player name change or review strip."""
    name_el = page.locator(".bid-player-name, [data-entry-player]")
    old_name = ""
    if name_el.count():
        old_name = (name_el.first.text_content() or "").strip()
    page.locator("#btn-next").click()
    page.wait_for_function(
        """([oldName]) => {
            const review = document.querySelector(
              '#scoresheet-review, .scoresheet-review, [data-scoresheet-review]');
            if (review) return true;
            const el = document.querySelector('.bid-player-name, [data-entry-player]');
            if (!el) return true;
            return (el.textContent || '').trim() !== oldName;
        }""",
        arg=[old_name],
        timeout=10000,
    )


def enter_score(page: Page, value: int) -> None:
    """Type digits (and ± if negative) then Next."""
    if value < 0:
        toggle_sign(page)
        value = abs(value)
    for ch in str(value):
        press_digit(page, int(ch))
    press_next(page)


def enter_scores_for_all(page: Page, scores: list[int]) -> None:
    for score in scores:
        enter_score(page, score)


def edit_review_row(page: Page, player_name: str) -> None:
    row = page.locator(f"{SEL_REVIEW} >> text={player_name}").locator("..")
    row.locator('button:has-text("Edit")').click()


def score_round(page: Page) -> None:
    page.locator(SEL_SCORE_ROUND).first.click()
    page.wait_for_function(
        "() => location.hash.includes('scoreboard')"
        " || location.hash.includes('intermission')"
        " || document.querySelector('[data-standings], [data-intermission]')",
        timeout=15000,
    )


def assert_standings_visible(page: Page, expect_visible: bool) -> None:
    standings = page.locator(SEL_STANDINGS)
    if expect_visible:
        expect(standings.first).to_be_visible(timeout=5000)
    else:
        assert standings.count() == 0 or not standings.first.is_visible()


def undo_last_round(page: Page) -> None:
    page.locator(SEL_UNDO_LAST).first.click()


def edit_completed_round(page: Page, round_index: int = -1) -> None:
    _ = round_index
    page.locator(SEL_EDIT_ROUND).first.click()


def play_one_scoresheet_round(page: Page, scores: list[int]) -> None:
    enter_scores_for_all(page, scores)
    score_round(page)


def block_game_sync_routes(page: Page) -> None:
    """Abort sync endpoints so entry stays local (mirrors IDB-first UI tests)."""

    def _abort(route):
        route.abort()

    page.route("**/api/**/sync-round**", _abort)
    page.route("**/api/sync**", _abort)
    page.route("**/api/**/import**", _abort)
