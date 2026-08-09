# Scokeep

**Live:** [scokeep.onrender.com](https://scokeep.onrender.com)

Ditch the notebook. Scokeep is a mobile-first score tracker built for Kachuful (Judgement). One person runs the app on their phone, taps in scores, and the math is done. No arguments, no miscalculations, no lost notebooks.

**Install it:** Open the site on your phone, tap "Add to Home Screen" — it runs like a native app (PWA with offline support).

## How It Works

1. **Create a Room** — give your group a name and a 4-digit PIN
2. **Add Players** — drag to set clockwise seating order
3. **Configure** — game mode, scoring rule, cards per round, must-lose toggle
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
- Auto-calculated max cards per round based on player count (52 ÷ players)

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
- **Cards per round:** configurable from 1 to max (auto-calculated: 8 for ≤6 players, 7 for 7, 6 for 8)
- **Alternating sets:** odd sets descend (8→1), even sets ascend (1→8)
- **Default:** 3 sets, configurable 1-5
- **Extend:** after the last round, add 1-4 more sets
- **Trump rotation:** ♠ → ♦ → ♣ → ♥ (repeating)

### Rooms & Multiplayer
- Persistent rooms — come back anytime with name + PIN
- Anyone with the PIN can join and take over scoring mid-game
- Resume active game within 30 minutes of inactivity
- Recent room names shown on join screen
- Players remembered between games
- Refresh-safe — reloading the page resumes exactly where you left off

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
              │   (Neon)    │
              └─────────────┘
```

### Tech Stack — Why These Choices

| Layer | Choice | Why |
|-------|--------|-----|
| **Backend** | FastAPI (Python) | Async-first, built-in validation via Pydantic, minimal boilerplate |
| **Frontend** | Vanilla JS (ES Modules) | Zero build step, no framework overhead, instant loading on mobile |
| **Database** | PostgreSQL (Neon serverless) | JSONB for flexible player data, serverless scales to zero when idle |
| **ORM** | SQLAlchemy async | Type-safe queries, connection pooling, no raw SQL |
| **Auth** | Signed cookies (itsdangerous) | No JWTs to manage, httponly+secure+samesite, 30-day sessions |
| **Hosting** | Render (Docker) | Auto-deploy from git, managed SSL, zero config |

### Data Consistency

Highest priority — no data is lost mid-game:

- **Every action persists immediately.** Each bid, hand entry, and round score is committed to the database before the API responds. No in-memory-only state.
- **Phase state machine** enforces valid transitions: `bidding → playing → round_end → scoreboard → bidding`. The server rejects out-of-order actions (e.g., submitting hands during bidding returns 409).
- **JSONB columns** for bids, hands_won, and scores — each round's data is stored atomically. Partial updates are impossible.
- **Refresh-safe.** Every screen calls `guardPhase()` on mount, which fetches the game's current state from the server and redirects to the correct screen if needed. Refreshing the browser always shows the real state.
- **30-minute game recovery.** If the app is closed, the game remains active and resumable for 30 minutes. Reopening the room shows "Resume Game."

### Connection Resilience

Built for serverless PostgreSQL where connections drop frequently:

- **`pool_pre_ping`** — every query pings the connection first; stale connections are replaced transparently
- **`pool_recycle=600`** — connections recycled every 10 minutes, before Neon's idle timeout kills them
- **Async throughout** — `asyncpg` driver with SQLAlchemy async sessions. No blocking I/O.
- **`func.now()` for timestamps** — all timestamps generated server-side in SQL, avoiding Python datetime timezone issues with asyncpg

### Security

- **PINs:** bcrypt-hashed, never stored in plaintext
- **Sessions:** signed httponly secure samesite=lax cookies. Can't be read by JavaScript or sent cross-site
- **IDOR protection:** every endpoint verifies the authenticated session's playground_id matches the requested resource. Tested with dedicated regression tests.
- **Rate limiting:** 5 requests/minute on the auth endpoint (slowapi)
- **XSS prevention:** server-side `html.escape()` at input boundary for all player names
- **Input validation:** Pydantic schemas on every endpoint with type, range, and pattern constraints
- **No secrets in code:** all credentials via environment variables, `.env` in `.gitignore`

### Scalability

Current scale: personal use (< 100 concurrent users). The architecture supports growth:

- **Stateless server** — all state lives in PostgreSQL. Multiple server instances can serve the same data.
- **Connection pooling** — SQLAlchemy pool handles concurrent requests without connection exhaustion.
- **No WebSockets** — pure REST. Each request is independent. Horizontal scaling is a load balancer away.
- **JSONB flexibility** — player count (2-8), bid values, and scores are stored in JSONB dicts. No schema migrations needed when game rules change.
- **Concurrent rooms** — each room is isolated by playground_id. Thousands of rooms can run simultaneously with no cross-talk.

To scale further: add Redis for session storage, move to managed PostgreSQL with read replicas, and add a CDN for static assets.

### Debugging & Observability

- **Client-side logger** — `window.__scokeepLogs` captures every API call, phase transition, and error. Available in browser console.
- **Phase resync** — if the client and server disagree on game phase, `guardPhase()` automatically redirects to the correct screen and logs the discrepancy.
- **Structured errors** — every API error returns `{"detail": "human-readable message"}` with appropriate HTTP status codes (400, 401, 403, 404, 409).

### Constants

All magic numbers live in `app/constants.py`, organized by section:

| Section | Constants |
|---------|-----------|
| Deck | `DECK_SIZE`, `MAX_PLAYERS`, `MIN_PLAYERS` |
| Game defaults | `DEFAULT_ROUNDS_PER_SET`, `DEFAULT_NUM_SETS`, `DEFAULT_MODE`, `DEFAULT_SCORING_FORMULA` |
| Session | `SESSION_COOKIE_NAME`, `SESSION_MAX_AGE_AUTH`, `SESSION_MAX_AGE_JOIN`, `ACTIVE_GAME_TTL_MINUTES` |
| Playground | `SHARE_CODE_LENGTH` |
| Awards | `HIGH_ROLLER_MIN_BID` |

### PWA

- Installable on iOS and Android home screens
- Service worker caches the app shell for instant loading
- Standalone display — no browser chrome
- Works offline for the UI; API calls need network

### Future Scope

- **Offline Quick Game** — play without network using IndexedDB for local storage. Architecture designed (see `architecture/quick-game.md`): shared game engine with pluggable storage backends, same screens, zero code duplication.

## Built With

Built using [agent-toolkit](https://github.com/anthropics/claude-code) — a skill-driven development framework with TDD workflows (/implementation, /debug, /evaluate, /reviewer, /precommit), automated quality gates, and structured report-based code review. Every feature follows the slab-by-slab cycle: failing test first, then implementation, then precommit gate. 316 tests covering scoring, game lifecycle, security, stats, and end-to-end flows.
