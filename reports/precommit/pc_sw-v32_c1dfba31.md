<!-- agent-toolkit:precommit | v1 | 2026-08-17 | c1dfba31 -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Pre-commit Report: sw-v32

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | precommit |
| Slug | sw-v32 |
| Date (UTC) | 2026-08-17 |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `/Users/jvalin/dev/st5/green_leaf/scokeep/.venv/bin/python3 -m pytest -q` | passed | ........................................................................ [ 16%] ........................................................................ [ 33%] .......................................… |
| lint  | `/Users/jvalin/dev/st5/green_leaf/scokeep/.venv/bin/python3 -m ruff check .` | passed | All checks passed! |

## Findings (agent-authored)

- Instructions: 1/1 addressed
- Test quality: skipped — Config only.
- Rules: 0 violation(s)
- README: PASS — No changes
- App verification: na — SW bump.

## Summary

Bump SW v31 to v32.

## Final Gate

[x] READY TO COMMIT
[ ] BLOCKED
