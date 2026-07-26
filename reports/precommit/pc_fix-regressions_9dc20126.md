<!-- agent-toolkit:precommit | v1 | 2026-07-26 | 9dc20126 -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Pre-commit Report: fix-regressions

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | precommit |
| Slug | fix-regressions |
| Date (UTC) | 2026-07-26 |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `.venv/bin/python -m pytest -q` | passed | ........................................................................ [ 32%] ........................................................................ [ 64%] .......................................… |
| lint  | `.venv/bin/python -m ruff check .` | passed | All checks passed! |

## Findings (agent-authored)

- Instructions: 2/2 addressed
- Test quality: verified — 223 tests pass, no sloppy assertions
- Rules: 0 violation(s)
- README: PASS — No README changes
- App verification: done — Verified bidding keypad max = cardsDealt, scoreboard branches by isGameOver

## Summary

Revert two regressions: keypad max no longer limited by previous bids, scoreboard shows last round between rounds and full table on game over.

## Final Gate

[x] READY TO COMMIT
[ ] BLOCKED
