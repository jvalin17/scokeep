<!-- agent-toolkit:precommit | v1 | 2026-09-28 | 9064e375 -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Pre-commit Report: podium-sw-cache

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | precommit |
| Slug | podium-sw-cache |
| Date (UTC) | 2026-09-28 |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `.venv/bin/python3 -m pytest -q --ignore=tests/ui` | passed | ........................................................................ [  5%] ........................................................................ [ 10%] .......................................… |
| lint  | `.venv/bin/python3 -m ruff check .` | FAILED | [1m[91mSIM114 [0m[[1m[96m*[0m] [1mCombine `if` branches using logical `or` operator[0m    [1m[94m-->[0m app/main.py:103:9     [1m[94m\|[0m [1m[94m101 \|[0m           path = request.u… |

## Findings (agent-authored)

- Instructions: 3/3 addressed
- Test quality: verified — test_service_worker_is_not_long_cached + test_service_worker_register_uses_version_query assert no-cache headers and index/register/sw version sync; 6 PWA tests passed
- Rules: 0 violation(s)
- README: PASS — No README behavior claims changed.
- App verification: pending — Reproduced Trial1 UIR2: API podium present, UI missing (CF HIT sw.js v76). After commit+promote, verify Awards shows The Podium without clearing site data.

## Summary

Fix CDN-pinned SW so Podium reaches clients after promote.

## Final Gate

[ ] READY TO COMMIT
[x] BLOCKED — lint re-run failed: .venv/bin/python3 -m ruff check .; app verification: still pending
