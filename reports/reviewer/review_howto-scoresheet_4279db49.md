<!-- agent-toolkit:reviewer | v1 | 2026-10-07 | 4279db49 -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Reviewer Report: How To Scoresheet section (home.js + tests)

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | reviewer |
| Slug | howto-scoresheet |
| Date (UTC) | 2026-10-07 |
| Areas reviewed | tests, ui, copy accuracy |

## Findings Summary

| Severity | Count |
|----------|-------|
| High | 0 |
| Medium | 1 |
| Low | 2 |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `.venv/bin/python3 -m pytest -q --ignore=tests/ui` | passed | ........................................................................ [  4%] ........................................................................ [  9%] .......................................… |
| lint  | `.venv/bin/python3 -m ruff check .` | passed | [1;32mAll checks passed![0m |


## Summary

**Status: FAIL** (1 medium copy mismatch).

|MEDIUM| `app/static/js/screens/home.js:46` | Step 3 says last player taps **Done** to reach round review; Scoresheet entry only exposes **Next** (`app/static/js/screens/entry.js:142`). No Done control exists in the dialer flow. |

**Copy vs UX (no other HIGH/MEDIUM):** Lobby Scoresheet tab and shared players; settings (label, Highest/Lowest total, show totals, allow negatives ±); buffer + Next dialer; Round review + Score Round; scoreboard Next Round / Finished / Undo Last Round / Edit Round; stats All / Judgement / Scoresheet; sync when round finished — all align with `game-settings.js`, `entry.js`, `scoreboard.js`, `stats.js`, and `requirements/multi-game.md`.

**Tests:** Removing the Scoresheet block (lines 41–50) fails vitest and `test_howto_includes_scoresheet_section` (needles are section-specific except `Undo Last Round`, which also appears in Judgement copy at line 58). Tests would not catch the Done/Next error.

**Fix:** Change line 46 to say tap **Next** to open **Round review** after the last player.

PASSED — no high-severity findings remain.

## Final Gate

[x] PASSED
[ ] BLOCKED
