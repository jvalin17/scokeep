<!-- agent-toolkit:reviewer | v1 | 2026-10-03 | 31a0816a -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Reviewer Report: playground stats game_type filter (post-fix re-review)

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
| Medium | 1 |
| Low | 2 |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `.venv/bin/python3 -m pytest -q --ignore=tests/ui` | FAILED | ........................................................................ [  5%] ........................................................................ [ 10%] .......................................… |
| lint  | `.venv/bin/python3 -m ruff check .` | passed | [1;32mAll checks passed![0m |


## Summary

Prior blockers are resolved: filter helpers live in app/services/stats_filter.py (analytics.py 494 lines, test_analytics_under_500_lines passes), empty typed filters use _build_empty_highlights() at analytics.py:79-85 (integration test_stats_filter_empty_typed_no_leaked_highlights), playground imports are ruff-clean, and six slab integration/unit filter tests pass in isolation.

MEDIUM: tests/unit/test_analytics.py:316-318 TestEmptyHighlightsSchema still inspects AnalyticsService.get_playground_stats source for career key strings; after extracting _build_empty_highlights() those keys no longer appear in that method, so full pytest --ignore=tests/ui fails (1 failed, 1418 passed). Update the test to assert against _build_empty_highlights() (test_decomposed_helpers.py already covers the helper lightly but not full key parity with _career_tables).

LOW (1): No direct unit tests for get_playground_stats branch matrix (insights nulling for scoresheet, cache bypass when typed); integration coverage is solid for happy paths and empty typed leak.

LOW (2): app/static/js/api.js:144-146 getPlaygroundStats still omits game_type query param; expected until FE stats/lobby slab wires typed tabs.

## Final Gate

[ ] PASSED
[x] BLOCKED — test re-run failed: .venv/bin/python3 -m pytest -q --ignore=tests/ui
