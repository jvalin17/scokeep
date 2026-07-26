<!-- agent-toolkit:precommit | v1 | 2026-07-26 | 23ff0d1b -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Pre-commit Report: datetime-fix

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | precommit |
| Slug | datetime-fix |
| Date (UTC) | 2026-07-26 |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `/Users/jvalin/dev/st5/green_leaf/scokeep/.venv/bin/python3 -m pytest -q` | passed | ........................................................................ [ 63%] .........................................                                [100%] =============================== warning… |
| lint  | `/Users/jvalin/dev/st5/green_leaf/scokeep/.venv/bin/python3 -m ruff check .` | passed | All checks passed! |

## Findings (agent-authored)

- Instructions: 1/1 addressed
- Test quality: verified — 113 tests passing
- Rules: 0 violation(s)
- README: PASS — OK
- App verification: done — Fixes prod crash

## Summary

Use naive UTC datetimes for PostgreSQL compatibility.

## Final Gate

[x] READY TO COMMIT
[ ] BLOCKED
