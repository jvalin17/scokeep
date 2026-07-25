# Scokeep

Mobile-first score tracker for Kachuful (Judgement) card game. Replaces notebook scoring with fast, error-free digital tracking.

## What it does

- **Blind score entry** via phone-style keypad (0-8) — scorekeeper doesn't see previous bids or totals
- **Three game modes:** Expert (no info shown), Rookie (trump + overbid indicator), Friendly (everything visible)
- **Playground system** — persistent groups with funky names, 4-digit PIN, shareable codes
- **Automatic scoring** — Kachuful standard formula with pluggable scoring engine
- **Must-lose mode** — bids can't equal cards dealt
- **Undo support** — revert last round with full score recalculation

## Tech Stack

- **Backend:** FastAPI (Python 3.12)
- **Frontend:** Vanilla JS SPA (hash-based routing)
- **Database:** SQLite (dev) / PostgreSQL via Neon (prod)
- **Hosting:** Render (Docker, free tier)

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Run

```bash
uvicorn app.main:app --port 8050 --reload
```

Open http://localhost:8050 — API docs at http://localhost:8050/docs

## Test

```bash
pytest tests/ -v
```

108 tests covering scoring engine, playground CRUD, game lifecycle, round management, scoreboard, and undo.

## API Endpoints

### Playground
- `POST /api/playground` — Create (name, PIN, players)
- `POST /api/playground/auth` — Authenticate (name + PIN)
- `GET /api/playground/:code` — Get by share code

### Game
- `POST /api/game` — Start new game
- `GET /api/game/:id` — Get game state
- `POST /api/game/:id/end` — End game early

### Round
- `POST /api/game/:id/bid` — Submit bid
- `GET /api/game/:id/bids` — Get all bids
- `PATCH /api/game/:id/bid/:idx` — Edit bid
- `POST /api/game/:id/start-round` — Confirm bids, start play
- `POST /api/game/:id/enter-round-end` — Transition to score entry
- `POST /api/game/:id/hands` — Submit hands won
- `POST /api/game/:id/end-round` — Calculate scores, advance

### Scoreboard
- `GET /api/game/:id/scoreboard` — Cumulative scores
- `GET /api/game/:id/history` — Round-by-round details
- `POST /api/game/:id/undo` — Undo last round

### Health
- `GET /api/health` — Server + DB status

## Scoring Rules (Kachuful Standard)

| Bid | Result | Points |
|-----|--------|--------|
| 0 | Made | +10 |
| 0 | Missed | -10 |
| 1 | Made | +11 |
| 1 | Missed | -11 |
| N (2-8) | Made | +N x 10 |
| N (2-8) | Missed | -N x 10 |

## Game Structure

- **Set:** 8 rounds (8, 7, 6, 5, 4, 3, 2, 1 cards)
- **Default:** 3 sets (24 rounds)
- **Trump rotation:** Spades, Diamonds, Clubs, Hearts (repeating)
- **Dealer:** Rotates clockwise each round

## Deploy

```bash
docker build -t scokeep .
docker run -p 8050:8050 -e DATABASE_URL=... scokeep
```

Or use `render.yaml` for Render deployment.
