<!-- agent-toolkit:reviewer | v1 | 2026-09-26 | 63702fc1 -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Reviewer Report: IDB-first SyncManager + lobby/game-api sync integrity (all review areas)

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | reviewer |
| Slug | idb-first |
| Date (UTC) | 2026-09-26 |
| Areas reviewed | code quality, tests, runtime, accessibility, dependencies, ui |

## Findings Summary

| Severity | Count |
|----------|-------|
| High | 2 |
| Medium | 6 |
| Low | 4 |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `.venv/bin/python3 -m pytest -q --ignore=tests/ui` | passed | ........................................................................ [  5%] ........................................................................ [ 10%] .......................................… |
| lint  | `.venv/bin/python3 -m ruff check .` | passed | [1;32mAll checks passed![0m |


## Summary

HIGH (2):
1. confirmFinal finalizes server game without guaranteeing round queue is drained — retrySyncQueue ignores non-OK HTTP (continues), then finalizeServerGameQuiet always runs (game-api.js:431-447, sync-manager.js:223-239). Risk: finished server game missing rounds → bad stats.
2. Lobby End Game always navigates to scoreboard even when end/confirmFinal fail (lobby.js:156-159 swallow errors). Server may stay active → Resume via getServerActiveGame fallback (lobby.js:32-39).

MEDIUM (6):
3. Online rooms force sync_pending=false (game-api.js:301-302) — failed round syncs have no lobby Sync-now recovery UI.
4. retrySyncQueue success does not set round.synced=true (sync-manager.js:231-233).
5. Dual IDB identity: createOnlineGame uses game-… id; loadGameFromServer may use numeric id (game-api.js:88-112, 296-304).
6. sync-round has no rate limit (sync.py:89-102) unlike import/create.
7. Last-write-wins upsert on sync-round/sync-state (sync.py:71-86, 115-118) — known single-scorer gap.
8. purgeOldGames unused and would orphan rounds if called (store.js:369-388).

LOW (4):
9. Duplicate isLocalId helpers (resolve-api.js / sync-manager.js).
10. Leftover api.js getGame/endGame unused by gameplay screens.
11. Empty catch in #withLock drain (sync-manager.js:84-86).
12. Lobby Sync checkPendingSyncs uses console.warn not logger (lobby.js:268-269).

A11y: Sync result has aria-live PASS; Sync button missing aria-busy; remove-player × lacks accessible name.
Deps: no new production deps — PASS.
UI false-success: End Game / confirmFinal return success path while server may still be active — tied to HIGH #2.

Gate: BLOCKED while high > 0.

## Final Gate

[ ] PASSED
[x] BLOCKED — high-severity findings: 2
