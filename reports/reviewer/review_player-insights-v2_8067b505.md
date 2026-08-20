<!-- agent-toolkit:reviewer | v1 | 2026-08-16 | 8067b505 -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Reviewer Report: Player insights — post-refactor review (code quality + tests + UI)

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | reviewer |
| Slug | player-insights-v2 |
| Date (UTC) | 2026-08-16 |
| Areas reviewed | code quality, tests, UI |

## Findings Summary

| Severity | Count |
|----------|-------|
| High | 5 |
| Medium | 12 |
| Low | 6 |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `/Users/jvalin/dev/st5/green_leaf/scokeep/.venv/bin/python3 -m pytest -q` | passed | ........................................................................ [ 18%] ........................................................................ [ 36%] .......................................… |
| lint  | `/Users/jvalin/dev/st5/green_leaf/scokeep/.venv/bin/python3 -m ruff check .` | passed | All checks passed! |


## Summary

HIGH (5): 1) Dead code: _calc_leaderboard, _calc_trends, _calc_player_stats still in analytics.py — never called. 2) Comeback threshold inconsistency: _FeatureAccumulator uses <2, _ExtrasAccumulator uses <4. 3) Integration tests all use 1-round games, not realistic multi-round. 4) test_stats_insights_after_three_games asserts structure only, not values. 5) stats.js:254 inline onclick handler (XSS risk with game_id). MEDIUM (12): Magic numbers in trend threshold (0.1), tempo threshold (3), consistency thresholds (30, 60), fun facts thresholds (40, 3, 4, 6). Missing constants. Personality metadata duplicated in Python and JS. _draft_assign O(n^3). Date formatting shows 'Invalid Date' for bad input. Zero bid streak continues across games (intentional but undocumented). LOW (6): EMA_ALPHA hardcoded. Centroids not runtime-configurable. Single source of truth for personality meta. No responsive font scaling. Webkit-only line-clamp. Global namespace pollution with window._expandGame.

## Final Gate

[ ] PASSED
[x] BLOCKED — high-severity findings: 5
