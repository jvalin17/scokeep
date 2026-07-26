# Scokeep

**Live:** [scokeep.onrender.com](https://scokeep.onrender.com)

Ditch the notebook. Scokeep is a mobile-first score tracker for Kachuful (Judgement) — the card game where predicting your hands is everything.

One person runs the app on their phone, taps in bids and results, and the math is done. No arguments, no miscalculations, no lost notebooks.

**Install it:** Open the site on your phone, tap "Add to Home Screen" — it runs like a native app.

## How It Works

1. **Create a Playground** — give your group a name and a 4-digit PIN
2. **Add Players** — drag the handle to set clockwise seating order
3. **Pick Settings** — game mode, number of sets, must-lose on/off
4. **Play Rounds** — tap the keypad for each player's bid, then their hands won at round end
5. **See Scores** — round scores after every round, full standings at game end

## Features

### Scoring
- Phone-style keypad (0-8) with haptic feedback and tap sound
- Instant advance — tap a number, move to the next player
- "Previous Player" button to go back and change
- Automatic score calculation — never wrong
- Undo last round if something was entered incorrectly

### Trump Display
- Large trump suit symbol (Spades, Diamonds, Chidi, Hearts) shown during bidding, play, and scoring
- Dealer name displayed on bidding screen

### Dealer Rotation
- Dealer rotates clockwise each round
- Bidding order starts from the player after the dealer
- Dealer always bids last (must-lose applies to dealer)

### Game Modes
| Mode | What's Visible |
|------|---------------|
| **Expert** | Cards to deal only. No trump, no bids, no scores during play |
| **Rookie** (default) | Large trump suit display below keypad |
| **Friendly** | Everything — all bids, trump, hands claimed count |

### Must-Lose Mode
The dealer (last to bid) cannot make the total bids equal the cards dealt. The forbidden number is greyed out on their keypad. Other players bid freely. On by default.

### Appearance
- **Standard** — clean, monochrome
- **Interactive** (default) — colorful phase backgrounds (yellow for bidding, green for play, blue for scoring, purple for results), larger text

### Playgrounds
- Persistent groups — come back anytime with name + PIN
- 4-character share code visible on all game screens
- Resume active game if one is in progress (within 10 minutes)
- Recent playground names shown on return screen
- Players remembered between games

### Analytics
Accessible from the lobby via the Stats button:
- **Leaderboard** — wins, win rate, average score, best/worst game
- **Bid Accuracy** — percentage bars showing how often each player makes their bid
- **Head-to-Head** — win record between every player pair
- **Game History** — last 20 games with scores and winners

### Game Structure
- **Set:** 8 rounds (8, 7, 6, 5, 4, 3, 2, 1 cards)
- **Default:** 3 sets (24 rounds), configurable 1-5
- **Trump:** Spades, Diamonds, Chidi, Hearts (repeating)
- **Dealer:** Rotates clockwise each round

### Scoring Rules

| Bid | Made | Missed |
|-----|------|--------|
| 0 | +10 | -10 |
| 1 | +11 | -11 |
| 2-8 | +N x 10 | -N x 10 |

### PWA
- Installable on phone home screen (iOS + Android)
- Cached app shell for fast loading
- Works offline for the UI (API calls need network)

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

117 tests: scoring engine, playground CRUD, game lifecycle, round management, scoreboard, undo, analytics, and end-to-end flows.
