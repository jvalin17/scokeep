<!-- agent-toolkit:precommit | v1 | 2026-08-17 | 933dcdc7 -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Pre-commit Report: promote

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | precommit |
| Slug | promote |
| Date (UTC) | 2026-08-17 |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `/Users/jvalin/dev/st5/green_leaf/scokeep/.venv/bin/python3 -m pytest -q` | passed | ........................................................................ [ 16%] ........................................................................ [ 33%] .......................................… |
| lint  | `/Users/jvalin/dev/st5/green_leaf/scokeep/.venv/bin/python3 -m ruff check .` | passed | All checks passed! |

## Findings (agent-authored)

- Instructions: 1/1 addressed
- Test quality: skipped — Shell script, no testable logic.
- Rules: 0 violation(s)
- README: PASS — No changes
- App verification: na — Deploy tooling.

## Summary

Add scripts/promote.sh — fast-forward merges main into prod with confirmation.

## Final Gate

[x] READY TO COMMIT
[ ] BLOCKED
