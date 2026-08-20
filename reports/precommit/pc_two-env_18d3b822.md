<!-- agent-toolkit:precommit | v1 | 2026-08-17 | 18d3b822 -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Pre-commit Report: two-env

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | precommit |
| Slug | two-env |
| Date (UTC) | 2026-08-17 |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `/Users/jvalin/dev/st5/green_leaf/scokeep/.venv/bin/python3 -m pytest -q` | passed | ........................................................................ [ 16%] ........................................................................ [ 33%] .......................................… |
| lint  | `/Users/jvalin/dev/st5/green_leaf/scokeep/.venv/bin/python3 -m ruff check .` | passed | All checks passed! |

## Findings (agent-authored)

- Instructions: 1/1 addressed
- Test quality: skipped — Config-only change (render.yaml).
- Rules: 0 violation(s)
- README: PASS — No README changes
- App verification: na — Infrastructure config.

## Summary

Add two-service render.yaml: prod watches prod branch, stable watches main branch.

## Final Gate

[x] READY TO COMMIT
[ ] BLOCKED
