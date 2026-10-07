<!-- agent-toolkit:reviewer | v1 | 2026-10-03 | 4b439492 -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Reviewer Report: Slab stats-filter-ui — stats screen game-type filter (FE)

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | reviewer |
| Slug | stats-filter-ui |
| Date (UTC) | 2026-10-03 |
| Areas reviewed | ui, tests, code quality, accessibility |

## Findings Summary

| Severity | Count |
|----------|-------|
| High | 0 |
| Medium | 1 |
| Low | 4 |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `.venv/bin/python3 -m pytest -q --ignore=tests/ui` | passed | ........................................................................ [  5%] ........................................................................ [ 10%] .......................................… |
| lint  | `.venv/bin/python3 -m ruff check .` | passed | [1;32mAll checks passed![0m |


## Summary

FE slab completes the stats-by-game-type feature: buildPlaygroundStatsPath/getPlaygroundStats pass game_type (api.js:150-160); stats screen renders All/Judgement/Scoresheet tablist, reloads on switch, hides Insights for scoresheet, shows scoresheet label in history (stats.js:30-31,63-77,82-83,346-391); lobby Stats navigates with selectedGameType (lobby.js:259-260); styling reuses lobby-game-tabs (.stats-game-type-tabs style.css:699). Integration matrix (test_stats_route_game_type_query_matrix) and UI filter isolation test cover the happy path; api-stats-query vitest locks URL shape.

MEDIUM (1): In-page game-type filter clicks update selectedGameType and reload data but do not call navigate() to sync location.hash (stats.js:140-152). Lobby entry and post-clear-stats use hash segments (lobby.js:260, stats.js:253), so after switching filters the URL is stale—refresh, share link, and back/forward can show the wrong filter. Fix: navigate(`stats/${shareCode}/${next}`) (or hash replace) on filter change.

LOW (1): Stats game-type tabs use role=tablist/tab and aria-selected but omit aria-controls present on lobby tabs (game-settings.js:44-48 vs stats.js:72-74)—minor a11y parity gap.

LOW (2): No vitest markup contract for stats filter tablist (contrast lobby-game-tabs.test.js); only buildPlaygroundStatsPath is unit-tested.

LOW (3): tests/ui/test_stats_game_type_filter.py uses fixed wait_for_timeout(500) after filter clicks (lines 49,54,60) instead of waiting on card count or network idle—increases flake risk.

LOW (4): requirements/multi-game.md open question #1 recommends disabling Insights on All until a typed filter is selected; stats.js:82 still shows Insights for all and kachuful. Product choice—align with PM or document as accepted.

Gate: no high findings; prior stats-filter-api backend concerns (empty typed highlights, analytics size) appear resolved in current tree. Mechanical pass depends on hook re-run.

PASSED — no high-severity findings remain.

## Final Gate

[x] PASSED
[ ] BLOCKED
