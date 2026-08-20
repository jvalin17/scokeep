<!-- agent-toolkit:precommit | v1 | 2026-08-20 | 255c0b09 -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Pre-commit Report: awards-thresholds

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | precommit |
| Slug | awards-thresholds |
| Date (UTC) | 2026-08-20 |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `/Users/jvalin/dev/st5/green_leaf/scokeep/.venv/bin/python3 -m pytest -q` | passed | ........................................................................ [ 16%] ........................................................................ [ 32%] .......................................… |
| lint  | `/Users/jvalin/dev/st5/green_leaf/scokeep/.venv/bin/python3 -m ruff check .` | passed | All checks passed! |

## Findings (agent-authored)

- Instructions: 3/3 addressed
- Test quality: verified — 442 tests — added 4 new award tests (wooden_spoon, on_fire, best_round, worst_round) plus all_keys test updated. Existing tests updated with new stats keys.
- Rules: 0 violation(s)
- README: PASS — No changes
- App verification: done — New awards render in Last Game section. Thresholds tuned for real Kachuful data.

## Summary

Tune consistency thresholds (30/60 → 60/120), add 10% bidding style margin, add 4 new last-game awards. 442 tests.

## Final Gate

[x] READY TO COMMIT
[ ] BLOCKED
