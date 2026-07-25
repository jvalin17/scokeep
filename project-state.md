# Project State
<!-- Auto-maintained by agent-toolkit skills. All skills read this at start, write at end. -->

## Core Intent
- **What:** Mobile-first score tracker for Kachuful (Judgement) card game — replaces notebook with blind, fast, error-free scoring
- **For whom:** Card game groups playing with physical cards
- **Current workflow:** Manual notebook tracking — prone to math errors, lost notebooks, arguments

## Last Skill Run
- **Skill:** /architecture
- **Date:** 2026-07-25
- **Status:** Complete — architecture doc written, all decisions made

## Key Decisions
| Decision | Made By | Date |
|----------|---------|------|
| App name: Scokeep | /requirements | 2026-07-25 |
| FastAPI API + Vanilla JS SPA (Option B) | /architecture | 2026-07-25 |
| PostgreSQL (Neon free tier) | /architecture | 2026-07-25 |
| No WebSockets v1 — single phone scorekeeper | /architecture | 2026-07-25 |
| No auth — PIN per playground | /architecture | 2026-07-25 |
| 3 game modes: Expert/Rookie/Friendly | /requirements | 2026-07-25 |
| 2 appearances: Standard/Interactive | /requirements | 2026-07-25 |
| Playground = persistent group with funky name | /requirements | 2026-07-25 |
| JSONB for bids/scores (flexible player count) | /architecture | 2026-07-25 |
| Pluggable scoring engine | /architecture | 2026-07-25 |
| Scoring: Bid 0=10, Bid 1=11, Bid N≥2=N×10, miss=negated | /requirements | 2026-07-25 |
| Must-lose mode: total bids ≠ cards dealt (all players) | /requirements | 2026-07-25 |
| 10s configurable review timer | /requirements | 2026-07-25 |
| Dealer rotation tracked, rotates clockwise | /requirements | 2026-07-25 |
| Set = 8 rounds (8→1 cards), default 3 sets | /requirements | 2026-07-25 |
| Room settings all in one section | /requirements | 2026-07-25 |
| Collect all data from day 1 for future analytics | /requirements | 2026-07-25 |

## Parking Lot
| Item | Parked By | Is Core Intent? | Status |
|------|-----------|-----------------|--------|
| Stats dashboard per playground | /requirements | No | v2 |
| Player leaderboard | /requirements | No | v2 |
| Real-time sync (WebSockets) | /requirements | No | v2 |
| Sound effects / haptics | /requirements | No | v2 |
| Export scorecard as image | /requirements | No | v2 |
| Other game presets (Rummy, etc.) | /requirements | No | v2 |
| Dark mode | /requirements | No | v2 |

## Active Warnings
- No warnings

## Feature Status
| Feature | Status | Last Verified |
|---------|--------|--------------|
| Playground CRUD | Not started | — |
| Game lifecycle | Not started | — |
| Bidding phase (keypad + queue) | Not started | — |
| Score entry (round end) | Not started | — |
| Scoring engine | Not started | — |
| Scoreboard | Not started | — |
| Trump/round display | Not started | — |
| Game modes (Expert/Rookie/Friendly) | Not started | — |
| Appearance (Standard/Interactive) | Not started | — |
| Dealer rotation | Not started | — |
| Must-lose mode | Not started | — |
| PWA (manifest + service worker) | Not started | — |

## Handoff Summaries

### /requirements -> /architecture
Core: Blind fast score entry for physical Kachuful games. Must-haves: playground persistence, phone keypad, 3 game modes, configurable settings. Watch out for: no auth (PIN only), must-lose mode applies to ALL players, flexible totals at round end.

### /architecture -> /implementation
Pattern: FastAPI API + Vanilla JS SPA + Neon PostgreSQL. Key decisions: 3 tables (playground, game, round), JSONB for flexible data, game state machine server-side, hash-based client routing. Watch out for: PIN must be bcrypt hashed, phase column enforces state transitions, scoring engine must be pluggable.

### /implementation -> /reviewer
<!-- Built: X. Tests: Y. Known gaps: Z. -->
