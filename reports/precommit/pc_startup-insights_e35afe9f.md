<!-- agent-toolkit:precommit | v1 | 2026-08-17 | e35afe9f -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Pre-commit Report: startup-insights

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | precommit |
| Slug | startup-insights |
| Date (UTC) | 2026-08-17 |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `/Users/jvalin/dev/st5/green_leaf/scokeep/.venv/bin/python3 -m pytest -q` | passed | ........................................................................ [ 16%] ........................................................................ [ 33%] .......................................… |
| lint  | `/Users/jvalin/dev/st5/green_leaf/scokeep/.venv/bin/python3 -m ruff check .` | passed | All checks passed! |

## Findings (agent-authored)

- Instructions: 1/1 addressed
- Test quality: verified — 433 tests passing. Startup recompute uses existing compute_insights which has 85 unit tests.
- Rules: 0 violation(s)
- README: PASS — No README changes
- App verification: done — Tested locally — insights recomputed on startup for all playgrounds.

## Summary

Recompute insights for all playgrounds during server startup lifespan hook. Ensures cached insights stay fresh after every deploy.

## Final Gate

[x] READY TO COMMIT
[ ] BLOCKED
