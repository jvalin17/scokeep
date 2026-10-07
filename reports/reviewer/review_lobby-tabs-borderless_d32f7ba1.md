<!-- agent-toolkit:reviewer | v1 | 2026-10-03 | d32f7ba1 -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Reviewer Report: Lobby game tabs borderless + tab-scoped resume + dialer keypad

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | reviewer |
| Slug | lobby-tabs-borderless |
| Date (UTC) | 2026-10-03 |
| Areas reviewed | ui, accessibility, tests, code quality |

## Findings Summary

| Severity | Count |
|----------|-------|
| High | 0 |
| Medium | 4 |
| Low | 3 |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `.venv/bin/python3 -m pytest -q --ignore=tests/ui` | passed | ........................................................................ [  5%] ........................................................................ [ 10%] .......................................… |
| lint  | `.venv/bin/python3 -m ruff check .` | passed | [1;32mAll checks passed![0m |


## Summary

**Borderless lobby tabs (confirmed):** Markup uses dual class `lobby-game-tabs stats-tabs` (`app/static/js/components/game-settings.js:42`). The more specific rule at `app/static/css/style.css:671-679` sets `border: none`, `background: transparent`, `box-shadow: none`, and `padding: 0`, overriding the bordered `.stats-tabs` track at `style.css:665`. Active tab shadow is cleared at `style.css:690-692`. Regression locked in `tests/js/theme-palette.test.js:31-38`.

**Tab-scoped Resume (pass):** `lobby-resume.js:10-15` gates resume on matching `game_type`; `lobby.js:43`, `54`, `89` wire initial tab + conditional resume block. Unit coverage in `tests/js/lobby-resume-tab.test.js`.

**Medium:** (1) **Accessibility** — No `:focus`/`:focus-visible` styles for `.stats-tab` or `.keypad-key`; only `input:focus, select:focus` at `style.css:124-127`, so keyboard focus on game-type tabs and dialer keys may be invisible. (2) **Accessibility** — Game-type tabs use `role="tablist"` / `role="tab"` (`game-settings.js:42-46`) but settings host `#lobby-settings-host` (`lobby.js:90-96`) lacks `role="tabpanel"`, `aria-labelledby`, or `aria-controls` linkage. (3) **Accessibility** — `.stats-tab` uses `font-size: 0.85rem` (`style.css:668`), below the 14px interactive minimum in reviewer a11y checks. (4) **Tests** — `renderGameTypeTabs` suites duplicate the same assertions in `tests/js/lobby-game-tabs.test.js:4-22` and `tests/js/game-settings.test.js:60-78`.

**Low:** (1) **Tests** — `lobby-game-tabs.test.js` never asserts `lobby-game-tabs` / `stats-tabs` classes on the tablist (only tab data attributes). (2) **UI** — Inactive tabs still use `background: var(--bg-card)` from base `.stats-tab` (`style.css:667-668`), so two adjacent pills can read as a light segment on `--bg-page` even without an outer track (acceptable; optional polish). (3) **Accessibility** — Keypad clear is long-press only on pointer (`score-dialer-keypad.js:66-74`); no keyboard equivalent.

**Dialer keypad:** Layout and ± disable behavior covered in `tests/js/score-dialer-keypad.test.js`; uses shared `.keypad` grid (`style.css:354-374`) with per-key borders (intended for dialer, not lobby tabs).

PASSED — no high-severity findings remain.

## Final Gate

[x] PASSED
[ ] BLOCKED
