<!-- agent-toolkit:reviewer | v1 | 2026-10-03 | 087b5283 -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Reviewer Report: Lobby borderless tabs re-review after medium fixes

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | reviewer |
| Slug | lobby-tabs-borderless-fix |
| Date (UTC) | 2026-10-03 |
| Areas reviewed | ui, accessibility, tests, code quality |

## Findings Summary

| Severity | Count |
|----------|-------|
| High | 0 |
| Medium | 0 |
| Low | 2 |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `.venv/bin/python3 -m pytest -q --ignore=tests/ui` | passed | ........................................................................ [  5%] ........................................................................ [ 10%] .......................................… |
| lint  | `.venv/bin/python3 -m ruff check .` | passed | [1;32mAll checks passed![0m |


## Summary

**Re-review vs prior report** (`reports/reviewer/review_lobby-tabs-borderless_d32f7ba1.md`): all four medium findings are **verified fixed** with file:line evidence.

**Medium fixes confirmed:** (1) `:focus-visible` on `.stats-tab` and `.keypad-key` at `app/static/css/style.css:671-675`. (2) Tab pattern: `role="tablist"` / `role="tab"` with `id`, `aria-controls`, and `aria-selected` in `app/static/js/components/game-settings.js:42-48`; `#lobby-settings-host` has `role="tabpanel"` and dynamic `aria-labelledby` in `app/static/js/screens/lobby.js:84-85`. (3) `.stats-tab` font-size `0.875rem` at `style.css:668` (14px minimum). (4) `renderGameTypeTabs` tests live only in `tests/js/lobby-game-tabs.test.js:4-27`; no duplicate in `tests/js/game-settings.test.js`.

**Additional verification (requested):** `renderResumeBlock` extracted to `app/static/js/screens/lobby-resume.js:33-45` and imported in `lobby.js:14,56`. Server active-game catch logs via `logger.warn` at `lobby.js:42`. Keypad `Delete` clears buffer at `app/static/js/components/score-dialer-keypad.js:97-103` with test `tests/js/score-dialer-keypad.test.js:66-75`. Label max 80 enforced in schema test `tests/unit/test_scoresheet_schema.py:51-55` (matches `maxlength="80"` in `game-settings.js:67`). UI regression `tests/ui/test_lobby_resume_tabs.py:15-31` asserts resume visibility only on matching tab.

**Borderless tabs (unchanged pass):** CSS override at `style.css:676-697`; CSS regression in `tests/js/theme-palette.test.js:31-44` including focus-visible and font-size assertions.

**Remaining low:** (1) **Accessibility** — Lobby game-type tabs declare ARIA tabs but implement click-only switching (`lobby.js:223-229`); no ArrowLeft/ArrowRight roving focus per reviewer tab keyboard guidance (still usable via Tab + Space/Enter). (2) **UI** — Inactive lobby tabs keep `background: var(--bg-card)` from base `.stats-tab` (`style.css:667-668`) on a transparent track; optional polish only.

Prior low items for missing tablist class assertion and Delete-key clear are **resolved** in tests/CSS/keypad.

PASSED — no high- or medium-severity findings remain.

PASSED — no high-severity findings remain.

## Final Gate

[x] PASSED
[ ] BLOCKED
