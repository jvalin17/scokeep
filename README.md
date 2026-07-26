# Scokeep

**Live:** [scokeep.onrender.com](https://scokeep.onrender.com)

Ditch the notebook. Scokeep is a mobile-first score tracker for Kachuful (Judgement) — the card game where predicting your hands is everything.

One person runs the app on their phone, taps in bids and results, and the math is done. No arguments, no miscalculations, no lost notebooks.

## How It Works

1. **Create a Playground** — give your group a name and a 4-digit PIN
2. **Add Players** — drag to set clockwise seating order
3. **Pick Settings** — game mode, number of sets, must-lose on/off
4. **Play Rounds** — tap the keypad for each player's bid, then their hands won at round end
5. **See Scores** — cumulative scoreboard updates after every round

## Features

### Scoring
- Phone-style keypad (0-8) for fast entry
- 3-second review timer with Next/Change buttons
- Automatic score calculation — never wrong
- Undo last round if something was entered incorrectly
- Flexible totals — warns if hands don't match cards dealt, but allows it

### Game Modes
| Mode | What's Visible |
|------|---------------|
| **Expert** | Cards to deal only. No trump, no bids, no scores during play |
| **Rookie** | Trump suit + "X of Y hands claimed" indicator |
| **Friendly** | Everything — all bids, trump, running scores |

### Must-Lose Mode
The last player to bid cannot make the total bids equal the cards dealt. The forbidden number is greyed out on their keypad. Other players bid freely.

### Appearance
- **Standard** — clean, monochrome
- **Interactive** — colorful phase backgrounds (yellow for bidding, green for play, blue for scoring, purple for results), larger text

### Playgrounds
- Persistent groups — come back anytime with name + PIN
- Share code lets others join a live game
- Recent playground names shown on return screen
- Players remembered between games

### Game Structure
- **Set:** 8 rounds (8, 7, 6, 5, 4, 3, 2, 1 cards)
- **Default:** 3 sets (24 rounds), configurable 1-5
- **Trump:** Spades, Diamonds, Clubs, Hearts (repeating)
- **Dealer:** Rotates clockwise each round

### Scoring Rules

| Bid | Made | Missed |
|-----|------|--------|
| 0 | +10 | -10 |
| 1 | +11 | -11 |
| 2-8 | +N x 10 | -N x 10 |

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

113 tests: scoring engine, playground CRUD, game lifecycle, round management, scoreboard, undo, and end-to-end flows.
