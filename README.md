# Scokeep

**Live:** [scokeep.onrender.com](https://scokeep.onrender.com)

Ditch the notebook. Scokeep is a mobile-first score tracker built for Kachuful (Judgement). One person runs the app on their phone, taps in scores, and the math is done. No arguments, no miscalculations, no lost notebooks.

**Install it:** Open the site on your phone, tap "Add to Home Screen" — it runs like a native app (PWA with offline support).

## How It Works

1. **Create a Room** — give your group a name and a 4-digit PIN
2. **Add Players** — drag to set clockwise seating order
3. **Configure** — game mode, scoring rule, sets, must-lose toggle
4. **Play Rounds** — tap bids and scores on the keypad
5. **See Stats** — leaderboard, accuracy, trends, awards

## Features

### Scoring
- Phone-style keypad with haptic feedback and tap sound
- Instant advance — tap a number, move to the next player
- Go back to previous player and edit anytime
- Inline editing on confirm screen — tap Edit next to any player
- Undo last round from the scoreboard
- End game from any screen

### Game Modes
| Mode | What You See | Best For |
|------|-------------|----------|
| **Expert** | Cards to deal only | Seasoned players |
| **Rookie** (default) | Trump suit shown | Regular players |
| **Friendly** | All bids, trump, scores | New players / teaching |

### Scoring Rules

Two scoring formulas, selectable before each game:

| Rule | Bid 0 Made | Bid 1 Made | Bid 2+ Made | Miss |
|------|-----------|-----------|-------------|------|
| **Ones** (default) | +10 | +11 | +N × 10 | Negated |
| **Zeros** | +10 | +10 | +N × 10 | Negated |

### Game Structure
- **Set:** 8 rounds (8→1 cards) or 4 rounds (test mode)
- **Alternating sets:** odd sets descend (8→1), even sets ascend (1→8)
- **Default:** 3 sets (24 rounds), configurable 1-5
- **Extend:** after the last round, add 1-4 more sets
- **Trump rotation:** ♠ → ♦ → ♣ → ♥ (repeating)

### Rooms & Multiplayer
- Persistent rooms — come back anytime with name + PIN
- Anyone with the PIN can join and take over scoring mid-game
- Resume active game within 30 minutes of inactivity
- Recent room names shown on join screen
- Players remembered between games

### Must-Lose Mode
Last player to bid cannot make total bids equal cards dealt. The forbidden number is greyed out. On by default.

### Appearance
- **Standard** — clean, monochrome
- **Interactive** (default) — phase-specific colors: yellow (bidding) → green (play) → blue (scoring) → indigo (scoreboard)

### Stats & Awards

**Tabs:**
- **Leaderboard** — wins, win rate, average score, best/worst game
- **Accuracy** — bid accuracy % bars per player
- **Trends** — win streaks, overbid/underbid ratios, clutch factor
- **Awards** — last game awards + career records
- **Games** — expandable scoresheets with trump suits and overbid/underbid colors

**Last Game Awards:** MVP, Sharpshooter, Brick Wall, Bold Move, Sandbagger, Gambler, Cursed

**Career Records:** Sniper, Zero Master, High Roller, All-in, Jinxed, Perfect Set

**Recent Form:** Hot Hand, On Fire, Streak, Dodger

## Architecture

```
┌─────────────────────────────────────────────┐
│                  Browser                     │
│  ┌─────────────────────────────────────────┐ │
│  │     Vanilla JS SPA (ES Modules)         │ │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌────────┐ │ │
│  │  │ Home │ │ Bid  │ │ Play │ │Scorebrd│ │ │
│  │  └──┬───┘ └──┬───┘ └──┬───┘ └──┬─────┘ │ │
│  │     └────────┴────────┴────────┘        │ │
│  │          Shared Utils Layer             │ │
│  │   (entry-utils, screen-parts, api.js)   │ │
│  └─────────────────┬───────────────────────┘ │
│                    │ fetch (JSON)             │
└────────────────────┼─────────────────────────┘
                     │
┌────────────────────┼─────────────────────────┐
│               FastAPI Server                  │
│  ┌─────────────────┴───────────────────────┐ │
│  │            Routes Layer                  │ │
│  │   /api/playground  /api/game  /api/round │ │
│  └─────────────────┬───────────────────────┘ │
│  ┌─────────────────┴───────────────────────┐ │
│  │           Services Layer                 │ │
│  │  Playground · Game · Round · Scoring     │ │
│  │  Analytics · Scoreboard                  │ │
│  └─────────────────┬───────────────────────┘ │
│  ┌─────────────────┴───────────────────────┐ │
│  │         Models (SQLAlchemy ORM)          │ │
│  │    Playground · Game · Round             │ │
│  └─────────────────┬───────────────────────┘ │
└────────────────────┼─────────────────────────┘
                     │
              ┌──────┴──────┐
              │ PostgreSQL  │
              │ (Neon free) │
              └─────────────┘
```

**State machine:** `bidding → playing → round_end → scoreboard → bidding`

**Security:** bcrypt PINs, signed httponly secure cookies, IDOR protection on all endpoints, rate limiting, server-side XSS sanitization.

## Built With

Built using [agent-toolkit](https://github.com/anthropics/claude-code) — a skill-driven development framework with TDD workflows (/implementation, /debug, /evaluate, /reviewer, /precommit), automated quality gates, and structured report-based code review.
