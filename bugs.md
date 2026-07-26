# Known Bugs & Issues

## Fixed This Session

### BUG-001: start-round accepts duplicate calls (FIXED)
- **Found by:** test_phase_transitions.py::test_double_start_round_rejected
- **Input:** POST /api/game/{id}/start-round when game is already in 'playing' phase
- **Expected:** 409 Conflict
- **Got:** 200 OK (silently re-processed)
- **Impact:** State corruption — could create duplicate rounds
- **Fix:** Added `if game.phase != "bidding"` check in routes/round.py:106

## Open Bugs

### BUG-002: XSS via player names
- **Severity:** High
- **Description:** Player names are interpolated raw into innerHTML across all game screens
- **Attack:** Create player with name `<img onerror=alert(1)>`
- **Affected files:** bidding.js:75, roundend.js:70, lobby.js:45, final.js:27, stats.js:77
- **Fix needed:** HTML escape utility before interpolation

### BUG-003: No cross-playground authorization
- **Severity:** Medium
- **Description:** Any authenticated user can operate on any game_id by guessing the integer ID
- **Example:** User authed to playground 1 can POST /api/game/999/bid if game 999 exists
- **Affected routes:** All game/round/score routes
- **Fix needed:** Check `game.playground_id == session.playground_id` in every route

### BUG-004: SSL verification disabled for database
- **Severity:** Medium
- **File:** app/database.py:23
- **Description:** `ssl_context.verify_mode = ssl_module.CERT_NONE` — disables TLS certificate verification for Neon DB connection
- **Risk:** Man-in-the-middle on DB connection
- **Fix needed:** Use proper CA certs or Neon's CA bundle

### BUG-005: No rate limiting on auth endpoint
- **Severity:** Medium
- **Endpoint:** POST /api/playground/auth
- **Description:** PIN is only 4 digits (10,000 combinations). No rate limiting means brute-force is trivial.
- **Fix needed:** slowapi rate limiter on auth endpoint (slowapi is already in deps)

### BUG-006: DRY violation — _require_auth duplicated
- **Severity:** Low (code quality)
- **Description:** `_require_auth()` function + `signer` instance duplicated identically in game.py, round.py, score.py
- **Fix needed:** Extract to shared auth module

### BUG-007: DRY violation — getTrump/getRoundCards duplicated in JS
- **Severity:** Low (code quality)
- **Description:** `getTrump()` and `getRoundCards()` copy-pasted in bidding.js, play.js, roundend.js
- **Fix needed:** Extract to shared utils module

## Test Gaps (no dedicated tests)

1. Free Score mode — scoring formula, game creation with free_rounds, full round flow
2. Analytics service — leaderboard calculation, bid accuracy, head-to-head, game history
3. Active game resume — TTL expiry, resume button logic
4. Recent playgrounds endpoint — response format, limit
5. Bid value validation for free mode (allows 0-999 but no server-side cards_dealt check)
