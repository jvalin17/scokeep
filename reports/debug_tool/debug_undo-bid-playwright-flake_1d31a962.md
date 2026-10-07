# Debug: Playwright undo bid flake on main

## Symptom
CI main push after PR #9: `test_undo_round_navigates_to_bidding` Timeout in `enter_bid` wait_for_function.

## Evidence
- Run https://github.com/jvalin17/scokeep/actions/runs/37581195013
- Local: 8/8 pass before harden; PR CI had passed (flake)

## Root cause
Post-undo hash flips to `bid/` before keypad remount finishes; first key tap can hit a dying keypad so player name never advances.

## Fix
- Wait for `.bid-player-name` + `#keypad-container` after undo
- `enter_bid` retries key tap up to 3x; prefer `#keypad-container` keys; use `:text-is`
