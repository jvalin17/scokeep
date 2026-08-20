<!-- agent-toolkit:precommit | v1 | 2026-08-20 | 337ca21c -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Pre-commit Report: tuck-danger

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | precommit |
| Slug | tuck-danger |
| Date (UTC) | 2026-08-20 |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `/Users/jvalin/dev/st5/green_leaf/scokeep/.venv/bin/python3 -m pytest -q` | passed | ........................................................................ [ 16%] ........................................................................ [ 32%] .......................................… |
| lint  | `/Users/jvalin/dev/st5/green_leaf/scokeep/.venv/bin/python3 -m ruff check .` | passed | All checks passed! |

## Findings (agent-authored)

- Instructions: 2/2 addressed
- Test quality: verified — 438 tests passing. UI-only changes.
- Rules: 0 violation(s)
- README: PASS — No changes
- App verification: done — End Game hidden under Options. Clear Stats under gear menu.

## Summary

Tuck dangerous actions behind toggles. End Game under Options in lobby. Clear Stats under gear in stats.

## Final Gate

[x] READY TO COMMIT
[ ] BLOCKED
