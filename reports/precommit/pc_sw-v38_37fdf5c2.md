<!-- agent-toolkit:precommit | v1 | 2026-08-20 | 37fdf5c2 -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Pre-commit Report: sw-v38

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | precommit |
| Slug | sw-v38 |
| Date (UTC) | 2026-08-20 |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `/Users/jvalin/dev/st5/green_leaf/scokeep/.venv/bin/python3 -m pytest -q` | passed | ........................................................................ [ 16%] ........................................................................ [ 32%] .......................................… |
| lint  | `/Users/jvalin/dev/st5/green_leaf/scokeep/.venv/bin/python3 -m ruff check .` | passed | All checks passed! |

## Findings (agent-authored)

- Instructions: 1/1 addressed
- Test quality: skipped — Config only.
- Rules: 0 violation(s)
- README: PASS — No changes
- App verification: na — SW bump.

## Summary

Bump SW v37 to v38.

## Final Gate

[x] READY TO COMMIT
[ ] BLOCKED
