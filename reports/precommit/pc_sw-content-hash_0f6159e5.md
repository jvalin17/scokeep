<!-- agent-toolkit:precommit | v1 | 2026-09-28 | 0f6159e5 -->
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
- Test quality: verified — Named tests cover resolve_shell_file, compute_shell_cache_name, render_service_worker, _service_worker_response
- Rules: 0 violation(s)
- README: PASS — No README claims changed.
- App verification: done — Stable EditScoreE2E + unit coverage for hashed SW

## Summary

Content-hashed service worker ready to commit.

## Final Gate

[x] READY TO COMMIT
[ ] BLOCKED
