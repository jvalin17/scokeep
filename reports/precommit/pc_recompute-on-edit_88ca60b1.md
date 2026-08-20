<!-- agent-toolkit:precommit | v1 | 2026-08-20 | 88ca60b1 -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Pre-commit Report: recompute-on-edit

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | precommit |
| Slug | recompute-on-edit |
| Date (UTC) | 2026-08-20 |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `/Users/jvalin/dev/st5/green_leaf/scokeep/.venv/bin/python3 -m pytest -q` | passed | ........................................................................ [ 16%] ........................................................................ [ 32%] .......................................… |
| lint  | `/Users/jvalin/dev/st5/green_leaf/scokeep/.venv/bin/python3 -m ruff check .` | passed | All checks passed! |

## Findings (agent-authored)

- Instructions: 1/1 addressed
- Test quality: verified — 5 integration tests passing. Recompute uses existing compute_insights (85 unit tests).
- Rules: 0 violation(s)
- README: PASS — No changes
- App verification: done — Score edit triggers full insights recompute for the playground.

## Summary

Call compute_insights after score correction to recalculate career records, highlights, and personalities.

## Final Gate

[x] READY TO COMMIT
[ ] BLOCKED
