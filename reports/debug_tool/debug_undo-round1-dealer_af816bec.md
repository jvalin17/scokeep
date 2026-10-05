# Debug Report: Undo round 1 rotates dealer

**Symptom:** Undo on first round changes who is dealing (moves to next person with 2 players).
**Expected:** Restart round 1 with the original dealer.
**Actual:** `dealer_index` decrements even though Next Round never advanced it.
**Root cause:** [H1] — undo always did `dealer_index - 1`; dealer only advances on `nextRound`/`advance_round`.
**Evidence:**
- `app/static/js/engine/game-engine.js` undoRound (was line 455) always rotated
- `app/services/scoreboard.py` undo_last_round always rotated
- Reproduction: vitest expected 0 got 1 with Alice/Bob after undo round 1
**Fix applied:** Only reverse dealer when undoing round > 1 (IDB + server).
**Regression test:** `tests/js/game-engine.test.js` `test_undo_round_1_keeps_original_dealer`; `tests/service/test_scoreboard_service.py::test_undo_round_1_keeps_original_dealer`
**Systemic risk:** none beyond these two undo paths (both fixed)
