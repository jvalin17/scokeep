<!-- agent-toolkit:evaluate | v1 | 2026-07-26 | 59c3df2b -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Evaluation: Scokeep project — full source evaluation (app/ and tests/)
# Score: **78%** (C+)

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | evaluate |
| Slug | scokeep |
| Date (UTC) | 2026-07-26 |
| Threshold | 95% |

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Completeness | 50% | 30% | 15 |
| Code Quality | 91% | 25% | 23 |
| Security | 100% | 20% | 20 |
| Test Quality | 75% | 15% | 11 |
| Efficiency | 95% | 10% | 10 |
| **Overall** | | | **78%** |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `/Library/Developer/CommandLineTools/usr/bin/python3 -m pytest -q` | FAILED | ImportError while loading conftest '/Users/jvalin/dev/st5/green_leaf/scokeep/tests/conftest.py'. tests/conftest.py:6: in <module>     from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmak… |
| lint  | `/Library/Developer/CommandLineTools/usr/bin/python3 -m ruff check .` | FAILED | /Library/Developer/CommandLineTools/usr/bin/python3: No module named ruff |


## Summary

Scokeep is a well-structured FastAPI + Vanilla JS score tracker for Kachuful card games. All core game flow features are implemented and 117 tests pass. However, several requirements gaps, security issues, and DRY violations prevent a higher score.

COMPLETENESS (74/100):
PASS — Create/join playground, PIN auth, share code, player management, bidding phase, hands entry, scoring engine, scoreboard, undo, dealer rotation, must-lose mode, game modes (Expert/Rookie/Friendly), appearance (Standard/Interactive), trump rotation, sets+rounds math, early game end, drag-to-reorder players, analytics/stats screen.
FAIL — Timer integration: `app/static/js/components/timer.js` exists and is fully implemented but is never imported or used in any screen (grep confirms zero imports). The 10s review window requirement (requirements.md lines 108, 119) is specified as must-have. The Timer component is dead code.
FAIL — Lobby shows only 1-5 sets (lobby.js:80) but requirements say 1-10 and schema supports ge=1 le=10 (game.py:12). UI truncates at 5.
FAIL — PWA (manifest + service worker) is listed as Not Started in project-state.md:63.
FAIL — 'Same players?' prompt at new game start (requirements.md:97) — lobby shows existing players but does not show a prompt comparing to last game's players with a confirm-or-edit flow.
PARTIAL — Rookie mode overbid/underbid indicator (requirements.md:65) — trump shown but no explicit over/underbid indicator per player during play.
PARTIAL — Confirm bids screen edit flow exists but uses client-side deletion only; PATCH /bid/:idx is called via editBid, which works, but the confirm screen in bidding.js:136 deletes from local bidsCollected and re-renders to keypad — does not call editBid API, so server state is inconsistent until re-submission. Fixed in handleBidSelect which does call editBid, but edit path from confirm screen (line 134-139) skips the API call.

CODE QUALITY (72/100):
FAIL — DRY: `_require_auth` function is copy-pasted identically in game.py:17-24, round.py:18-25, score.py:17-24. Also `signer = URLSafeSerializer(settings.secret_key)` duplicated 4 times. Should be in a shared auth module.
FAIL — DRY: `getRoundCards()` and `getTrump()` are copy-pasted in bidding.js:33-44, play.js:17-27, roundend.js:25-37 — three identical copies. These should be in a shared utils module.
FAIL — DRY: freescore.js:5-19 duplicates the full `request()` function and `BASE` constant from api.js instead of importing.
FAIL — Dead code: Timer component (timer.js) is built but never used in any screen — confirmed by grep finding zero imports. The `timer_seconds` game setting is stored but never read in any frontend screen.
FAIL — Test comment mismatch: test_playground_service.py:35 method name says '8_chars' but asserts len == 4 (line 40). SHARE_CODE_LENGTH = 4 in service.
PASS — Functions are generally under 30 lines. No god classes. Naming is descriptive. SOLID mostly followed. Imports clean. No silent catches on real errors.
PASS — Services are separated cleanly from routes. Scoring engine is pluggable.

SECURITY (68/100):
FAIL — XSS: User-controlled player names and playground names are interpolated directly into innerHTML via template literals across bidding.js:75, roundend.js:70, lobby.js:45, final.js:27/34, stats.js:77/105/150. No HTML escaping. A player named `<script>alert(1)</script>` would execute. This is a real attack surface since names come from the database (user-submitted at playground creation).
FAIL — No authorization check that the authenticated playground_id from the session actually owns the game_id being operated on. Any authenticated user can bid on, end, or undo any game by guessing a game_id. Routes verify a valid session exists but not that game.playground_id == session.playground_id (confirmed by grep finding no comparison).
FAIL — SSL: app/database.py:23 sets `ssl_context.verify_mode = ssl_module.CERT_NONE` and `ssl_context.check_hostname = False` — disables TLS certificate verification for the database connection. Susceptible to MITM on the DB connection.
FAIL — No rate limiting on public endpoints (create playground, auth playground) — brute-force PIN attempts are unrestricted.
FAIL — Bid value schema (round.py:8,12,17) allows values 0-999 but the game max is 8 cards. No server-side enforcement that bid <= cards_dealt. Client relies on keypad max but API allows arbitrary values.
PASS — PIN is bcrypt-hashed (PlaygroundService._hash_pin). No hardcoded secrets. Session cookies are httponly+samesite=lax. No SQL injection (parameterized queries via SQLAlchemy ORM). .env.example exists. No secrets in logs.

TEST QUALITY (82/100):
PASS — 117 tests all pass. Specific value assertions throughout (assertEqual, exact dict comparison). Unit tests cover scoring, trump, round service, game service, playground service, scoreboard service. Integration tests cover all API endpoints with realistic data flows.
PASS — Edge cases covered: must-lose mode, duplicate bids, wrong phase, missing bids, undo with no rounds, nonexistent IDs, wrong PIN, missing session.
PASS — test_full_game_flow.py uses realistic frontend settings and exercises complete round lifecycle.
PASS — Scoring engine has a full 8-round game simulation with hand-calculated expected values (test_scoring.py:82-150).
FAIL — Test name vs assertion mismatch: test_share_code_is_8_chars_alphanumeric (test_playground_service.py:35) asserts len == 4, not 8. Misleading test name — would pass for wrong reasons if someone reads the name.
FAIL — No tests for XSS or injection attack strings in player names.
FAIL — No tests verifying the Timer component integration (since it's not integrated — no tests would catch this missing feature).
FAIL — No test for cross-playground game access (security gap where any session can operate on any game_id).
PARTIAL — Loading states have try/finally missing in some JS screens (e.g., play.js:83 uses alert() on error instead of proper error element, no spinner cleanup). Timer component has proper cleanup via el.destroy.

EFFICIENCY (78/100):
PASS — No N+1 queries. Analytics service fetches all games then all rounds in 2 queries and processes in-memory.
PASS — No over-engineering. Stack is appropriate for scale (FastAPI, SQLite/Postgres, Vanilla JS).
PASS — Dependencies are lean: FastAPI, SQLAlchemy async, bcrypt, itsdangerous, pydantic-settings, httpx for tests.
FAIL — freescore.js makes 2N+3 sequential API calls per round save (one bid per player, one start-round, one enter-round-end, one hands per player, one end-round) instead of a batch endpoint. For 8 players this is 19 sequential HTTP requests. Not critical at current scale but wasteful.
FAIL — Active game lookup (game.py:62) uses `datetime.utcnow()` which is deprecated in Python 3.12 in favor of `datetime.now(UTC)`. Still works but will generate deprecation warnings in future versions.
PASS — Caching not prematurely added. No unnecessary abstraction layers.

## Final Gate

[ ] PASSED
[x] BLOCKED — test re-run failed: /Library/Developer/CommandLineTools/usr/bin/python3 -m pytest -q; lint re-run failed: /Library/Developer/CommandLineTools/usr/bin/python3 -m ruff check .; score 78 below threshold 95
