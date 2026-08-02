# Scokeep

**Live:** [scokeep.onrender.com](https://scokeep.onrender.com)

Ditch the notebook. Scokeep is a mobile-first score tracker built for Kachuful (Judgement). One person runs the app on their phone, taps in scores, and the math is done. No arguments, no miscalculations, no lost notebooks.

**Install it:** Open the site on your phone, tap "Add to Home Screen" — it runs like a native app.

## How It Works

1. **Create a Playground** — give your group a name and a 4-digit PIN
2. **Add Players** — drag the handle to set clockwise seating order
3. **Configure** — pick game mode, appearance, number of sets, must-lose toggle
4. **Play Rounds** — tap bids/scores on the keypad, instant advance to next player
5. **See Stats** — leaderboard, bid accuracy, head-to-head, game history

## Features

### Scoring
- Phone-style keypad with haptic feedback and tap sound
- Instant advance — tap a number, move to the next player
- "Previous Player" button to go back and change
- Inline bid editing on the confirm screen — tap Edit next to any player
- Automatic score calculation — never wrong
- Undo last round if something was entered incorrectly
- End game from any screen (bidding, play, round end, scoreboard)
- Between rounds: only that round's scores shown (no cumulative spoilers)

### Trump Display
- Large trump suit symbol (Spades, Diamonds, Clubs, Hearts)
- Shown during bidding, play, and scoring phases (Rookie/Friendly modes)
- Dealer name shown on bidding screen

### Dealer Rotation
- Dealer rotates clockwise each round
- Bidding order starts from the player after the dealer
- Dealer always bids last (must-lose restriction applies to last bidder)

### Game Modes
| Mode | What's Visible |
|------|---------------|
| **Expert** | Cards to deal only. No trump, no bids, no scores during play |
| **Rookie** (default) | Trump suit display below keypad |
| **Friendly** | Everything — all bids, trump, hands claimed count |

### Must-Lose Mode
The last player to bid cannot make the total bids equal the cards dealt. The forbidden number is greyed out on their keypad. On by default in the UI.

### Appearance
- **Standard** — clean, monochrome
- **Interactive** (default) — phase-specific background colors that shift as the game progresses: yellow (bidding) → green (play) → blue (scoring) → indigo (scoreboard) → purple (home)

### Playgrounds
- Persistent groups — come back anytime with name + PIN
- 4-character share code visible on all game screens
- Resume active game if one is in progress (within 10 min)
- Recent playground names shown on join screen
- Players remembered between games

### Analytics
Per-playground stats accessible from the lobby:
- **Leaderboard** — wins, win rate, average score per round, best/worst game
- **Bid Accuracy** — visual percentage bars showing how often each player makes their bid
- **Head-to-Head** — win record between every player pair
- **Game History** — expandable scoresheets with overbid/underbid color coding

### Scoring Rules

| Bid | Made | Missed |
|-----|------|--------|
| 0 | +10 | -10 |
| 1 | +11 | -11 |
| 2-8 | +N x 10 | -N x 10 |

### Game Structure
- **Set:** 8 rounds (8, 7, 6, 5, 4, 3, 2, 1 cards) or 4 rounds (test mode)
- **Alternating sets:** odd sets descend (8→1), even sets ascend (1→8)
- **Default:** 3 sets (24 rounds), configurable 1-5
- **Trump:** Spades, Diamonds, Clubs, Hearts (repeating)

### Security
- PIN hashed with bcrypt
- Signed httponly session cookies
- All endpoints verify playground ownership (no cross-playground access)
- Rate limiting on auth endpoint
- Server-side input sanitization (XSS prevention)

## Technical Details

### State Consistency
The game uses an explicit phase state machine: `bidding → playing → round_end → scoreboard → bidding`. Round advancement only happens when the scorekeeper taps "Next Round" — no auto-advancing, no race conditions. Anyone joining mid-game sees the real current state.

### Connection Resilience
Built for Neon PostgreSQL (serverless) + Render free tier, where connections drop frequently:
- **`pool_pre_ping`** — every database query pings the connection first; stale connections are replaced transparently
- **`pool_recycle=600`** — connections are recycled every 10 minutes, before Neon's idle timeout
- **Game TTL** — active games expire after 10 minutes of inactivity, preventing stale game state from confusing returning players

### asyncpg Compatibility
SQLAlchemy's asyncpg dialect converts Python naive datetimes to timezone-aware before sending to PostgreSQL, which rejects them for `TIMESTAMP WITHOUT TIME ZONE` columns. All timestamp defaults use `func.now()` — generating server-side `NOW()` in SQL, bypassing the Python datetime conversion entirely.

### PWA
- Installable on phone home screen (iOS + Android)
- Service worker caches the app shell for instant loading
- Works offline for the UI; API calls need network
- Standalone display — no browser chrome

### Pluggable Scoring
Scoring formulas are registered in a dictionary. Adding a new game's scoring rules is one function + one dict entry:
- `kachuful_standard` — bid/actual comparison with bonus scaling

## Development

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --port 8050 --reload
```

Open http://localhost:8050

### Tests

```bash
pytest tests/ -v
```

### CI

GitHub Actions runs the agent-toolkit quality gate on every push — tests, lint, and skill report verification.
