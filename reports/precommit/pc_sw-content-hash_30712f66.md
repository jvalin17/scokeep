<!-- agent-toolkit:precommit | v1 | 2026-09-28 | 30712f66 -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Pre-commit Report: sw-content-hash

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | precommit |
| Slug | sw-content-hash |
| Date (UTC) | 2026-09-28 |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `.venv/bin/python3 -m pytest -q --ignore=tests/ui` | passed | ........................................................................ [  5%] ........................................................................ [ 10%] .......................................… |
| lint  | `.venv/bin/python3 -m ruff check .` | passed | [1;32mAll checks passed![0m |

## Findings (agent-authored)

- Instructions: 3/3 addressed
- Test quality: verified — tests/unit/test_service_worker.py: hash changes when shell file changes; /sw.js no-cache + injected CACHE_NAME. TestPWAAssets: /sw.js alias matches, no-cache. 11 passed. Stable E2E EditScoreE2E confirmed post-game edit + awards.
- Rules: 0 violation(s)
- README: PASS — No README claims changed.
- App verification: done — Stable EditScoreE2E V622: played 2 rounds, edited review hands, awards/history showed Alice -20 Bob 0. Local render_service_worker yields scokeep-<12hex>.

## Summary

Content-hashed service worker fixes CDN stickiness without manual version bumps.

## Final Gate

[ ] READY TO COMMIT
[x] BLOCKED — TDD: 1 new function(s) without tests — app/main.py: new function '_service_worker_response' has no corresponding test
