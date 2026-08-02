# Known Bugs & Issues

## Fixed This Session (Session 5)

### BUG-001: start-round accepts duplicate calls (FIXED — Session 4)
- **Fix:** Added `if game.phase != "bidding"` check in routes/round.py:106

### BUG-002: XSS via player names (FIXED — Session 5)
- **Fix:** `html.escape()` at input boundary via `app/utils/sanitize.py`
- **Applied in:** `services/playground.py:41`, `services/game.py:45`
- **Tests:** `test_security.py::TestXSSPrevention` (2 tests), `test_sanitize.py` (14 unit tests)

### BUG-003: No cross-playground authorization (FIXED — Session 5)
- **Fix:** `get_game_with_auth()` in `app/utils/auth.py` checks `game.playground_id == playground_id`, returns 403
- **Applied in:** All game/round/score routes
- **Tests:** `test_security.py::TestCrossPlaygroundAuth` (5 tests)

### BUG-004: SSL verification disabled (FIXED — Session 5)
- **Fix:** Removed `check_hostname=False` and `verify_mode=CERT_NONE` from `app/database.py`
- Uses `ssl.create_default_context()` which verifies certificates by default

### BUG-005: No rate limiting on auth (FIXED — Session 5)
- **Fix:** Added `slowapi` limiter: `5/minute` on `POST /api/playground/auth`
- **Config:** `RATE_LIMIT_ENABLED` env var (disabled in tests)
- **Files:** `app/routes/playground.py`, `app/main.py`

### BUG-006: DRY — _require_auth duplicated (FIXED — Session 5)
- **Fix:** Extracted to `app/utils/auth.py` — shared `require_auth` and `get_game_with_auth`
- **Tests:** `test_auth.py` (6 unit tests)

### BUG-007: DRY — getTrump/getRoundCards duplicated in JS (FIXED — Session 5)
- **Fix:** Extracted to `app/static/js/components/game-utils.js`
- Drag reorder also extracted to `app/static/js/components/drag-reorder.js`

### BUG-008: routeMap used before declaration in app.js (FIXED — Session 5)
- **Found by:** code quality agent during /evaluate
- **File:** `app/static/js/app.js:73-74`
- **Fix:** Moved `const routeMap = {...}` above the `logger.resync()` call that uses it

### BUG-009: End Game button missing from confirm-bids screen (FIXED — Session 9)
- **Fix:** Added `#end-game-btn` button + click handler to `renderConfirm()` in `bidding.js:155-197`
- **Tests:** `test_full_simulation.py::TestEndGameFromAnyPhase` (3 regression tests)

### BUG-010: "Chidi" typo in trump names (FIXED — Session 9)
- **Fix:** Changed `'Chidi'` to `'Clubs'` in `game-utils.js:21`

### BUG-011: IDOR on stats endpoints (FIXED — Session 9)
- **Fix:** Added `playground.id != playground_id` check returning 403 in `playground.py:128,143`
- **Tests:** `test_security.py::TestStatsEndpointAuth` (3 regression tests)

### BUG-012: Lobby defaults mismatch — NOT A BUG
- **Ruling:** Rookie/Interactive are the intended UI defaults per user. Requirements doc said Expert/Standard but user overrides that decision.

### BUG-013: Dead code — free_raw in scoring.py (FIXED — Session 9)
- **Fix:** Removed unused `free_raw` function and its SCORING_FORMULAS entry

### BUG-014: Overlapping overbid/underbid colors in scoresheet (FIXED — Session 9)
- **Fix:** Changed `border-bottom` to `border` on `.scoresheet th, td` in `style.css:457`

### BUG-015: IDOR on game creation (FIXED — Session 9)
- **Fix:** Added `data.playground_id != playground_id` check returning 403 in `game.py:21`
- **Tests:** `test_security.py::TestGameCreateAuth` (2 tests)

### BUG-016: IDOR on active game query (FIXED — Session 9)
- **Fix:** Added `playground_id != auth_playground_id` check returning 403 in `game.py:33`
- **Tests:** `test_security.py::TestActiveGameAuth` (2 tests)

## Open Issues

### ISSUE-001: .env with production credentials tracked in git
- **Severity:** Critical
- **Description:** `.env` is in `.gitignore` but was committed before gitignore was added
- **Fix needed:** `git rm --cached .env` and rotate Neon DB credentials
- **Note:** Requires user action — credential rotation cannot be automated

### ISSUE-002: Frontend screens don't use escapeHtml()
- **Severity:** Low (mitigated by backend sanitization)
- **Description:** `escapeHtml()` exists in `game-utils.js` but frontend screens still use raw template literals for player names
- **Mitigation:** Backend sanitizes at input boundary, so stored names are already escaped
- **Fix needed:** Defense-in-depth — use `escapeHtml()` in all innerHTML template literals

### ISSUE-003: lobby.js still 245 lines
- **Severity:** Low (code quality)
- **Description:** Exceeds 200-line guideline. Drag reorder was extracted but remaining HTML template + event handlers are irreducible for a single screen.

### ISSUE-004: CI gate fails — `.venv/bin/python` not found
- **Severity:** High (blocks all CI runs)
- **Description:** `gates.json` has `"test_command": ".venv/bin/python -m pytest -q"` and `"lint_command": ".venv/bin/python -m ruff check ."` but CI installs packages into system Python (no `.venv`). The attestation script gets `[Errno 2] No such file or directory: '.venv/bin/python'`.
- **Fix needed:** Change both commands in `gates.json` to `"python -m pytest -q"` and `"python -m ruff check ."`. Works locally (venv activated = `python` resolves to venv) and in CI (system python).
- **File:** `gates.json:7-8`

### ISSUE-005: CI picks wrong evaluate report (mtime problem)
- **Severity:** High (blocks CI gate)
- **Description:** `reports.py:latest_report()` sorts reports by filesystem `st_mtime` to find the latest. After `git checkout` in CI, all files get the same timestamp, so the function picks an arbitrary report. It picked `eval_bug-fixes-session5_5c2c4dd7.md` (93%) instead of the latest `eval_scokeep-v1-s9-v3_7629dfee.md` (94%).
- **Fix needed:** Either (a) change `latest_report()` to parse the date from the report header instead of relying on mtime, or (b) remove old evaluate reports so only the latest exists.
- **File:** `.agent-toolkit/gate/reports.py:29-45`

## Test Gaps (remaining)

1. Analytics service — no dedicated test (user said to ignore)
2. Free Score mode — no dedicated test (user said to ignore)
3. ~~Playground stats endpoint — no test~~ (Fixed: 6 tests in test_stats.py)
