<!-- agent-toolkit:reviewer | v1 | 2026-10-03 | 9e279623 -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Reviewer Report: Slab stats-filter-api — playground stats game_type filter

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | reviewer |
| Slug | stats-filter-api |
| Date (UTC) | 2026-10-03 |
| Areas reviewed | code quality, tests, security |

## Findings Summary

| Severity | Count |
|----------|-------|
| High | 0 |
| Medium | 2 |
| Low | 2 |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `.venv/bin/python3 -m pytest -q --ignore=tests/ui` | FAILED | ........................................................................ [  5%] ........................................................................ [ 10%] .......................................… |
| lint  | `.venv/bin/python3 -m ruff check .` | FAILED | [1m[91mI001 [0m[[1m[96m*[0m] [1mImport block is un-sorted or un-formatted[0m   [1m[94m-->[0m app/routes/playground.py:3:1    [1m[94m\|[0m [1m[94m 1 \|[0m   """Playground API routes —… |


## Summary

Backend filter is well-structured: module-level game_type_of / filter_games_by_type, get_playground_stats scopes games/rounds/highlights, skips mixed insights cache when game_type is kachuful|scoresheet (analytics.py:115-118), strips ML insights for scoresheet (94-96), and history exposes game_type + label (_game_to_history 420-421). Route uses FastAPI Literal["all","kachuful","scoresheet"] with 422 on invalid values (playground.py:165; integration test_stats_filter_invalid_game_type_422). Auth + playground IDOR check unchanged. Six slab tests pass in isolation.

MEDIUM (1): When the filtered game list is empty, get_playground_stats still returns fallback highlights from the full playground insights blob (analytics.py:97-106) while total_games is 0 — inconsistent with the non-empty path that passes insights=None into _resolve_highlights for typed filters (115-118). If playground.insights.highlights is populated (e.g. after Judgement backfill) and the client requests the other game_type with no matching finished games, highlights can disagree with total_games/history. Fix: use _build_empty_highlights() (and align insights stripping) whenever game_type is not "all" and len(games)==0.

MEDIUM (2): analytics.py now exceeds the repo guard test_analytics_under_500_lines (test_dead_code_removed.py:47-53); full pytest --ignore=tests/ui reports 1 failed (1417 passed). Trim or split analytics before merge.

LOW (1): No unit tests for get_playground_stats branches (empty typed filter, insights nulling, cache bypass); coverage is integration-only.

LOW (2): app/static/js/api.js getPlaygroundStats does not yet pass game_type — expected if a separate FE slab wires lobby/stats tabs.

Must-fix before reviewer gate PASS: resolve test_analytics_under_500_lines failure (mechanical). Address empty-filter highlights consistency before relying on typed stats in UI.

## Final Gate

[ ] PASSED
[x] BLOCKED — test re-run failed: .venv/bin/python3 -m pytest -q --ignore=tests/ui; lint re-run failed: .venv/bin/python3 -m ruff check .
