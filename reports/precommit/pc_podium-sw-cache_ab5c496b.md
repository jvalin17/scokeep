<!-- agent-toolkit:precommit | v1 | 2026-09-28 | ab5c496b -->
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
| lint  | `.venv/bin/python3 -m ruff check .` | passed | [1;32mAll checks passed![0m |

## Findings (agent-authored)

- Instructions: 3/3 addressed
- Test quality: verified — PWAAssets tests assert no-cache on sw.js in prod mode and index/register/sw share ?v=82; 19 security+PWA tests passed; ruff clean
- Rules: 0 violation(s)
- README: PASS — No README behavior claims changed.
- App verification: done — Verified via ASGI client: GET /static/sw.js with debug=False returns Cache-Control no-cache; index embeds sw-register.js?v=82; register embeds sw.js?v=82; CACHE_NAME scokeep-v82. Prod Trial1 UI fix requires promote of this commit.

## Summary

Fix CDN-pinned SW so Podium reaches clients after promote.

## Final Gate

[x] READY TO COMMIT
[ ] BLOCKED
