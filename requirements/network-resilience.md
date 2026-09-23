# Network Resilience — Auto-Retry + Offline Failsafe

## Problem Statement

When internet drops during a server game, API calls hang (now timeout after 15s) and the game is stuck until connectivity returns. Users playing with physical cards can't wait — they need to keep scoring without interruption.

## Core Intent

**Never lose a game in progress.** If the network drops, the user keeps playing seamlessly. When internet returns, everything syncs back.

## User Flow

```
1. User is playing a server game (game 143, 5 players, round 12)
2. Internet drops
3. API call fails → auto-retry 3 times (1s, 2s, 4s backoff)
4. "Reconnecting..." banner appears at top
5. If retry succeeds → banner disappears, game continues normally
6. If all 3 retries fail → "Playing offline — will sync when back online" banner
7. Game switches to local JS engine (IndexedDB)
8. User continues playing: bids, hands, scoring — all local
9. Internet returns → browser detects online event
10. App syncs all offline rounds to server via import endpoint
11. Banner: "Synced ✓" → disappears after 3s
```

## Feature 1: Auto-Retry with Backoff

### Must
- Retry failed API calls 3 times with exponential backoff (1s, 2s, 4s)
- Show "Reconnecting..." banner at top of screen during retries
- Banner is non-blocking — user can see the game state underneath
- If retry succeeds, banner disappears, response is returned normally
- If all retries fail, throw the error (caught by Feature 2)
- Only retry on network errors and timeouts — NOT on 4xx/5xx responses
- Retry logic lives in `api.js:request()` — all server API calls get it automatically

### Must Not
- Don't retry POST requests that already succeeded (idempotency risk)
- Don't retry 4xx errors (client errors — retrying won't help)
- Don't show retry banner for Quick Game (local) calls

## Feature 2: Offline Failsafe

### Must
- When auto-retry exhausts (3 failures), switch game to offline mode
- Capture current game state (players, settings, current_round, dealer_index, bids so far)
- Create a local Quick Game in IndexedDB mirroring the server game state
- Continue gameplay using the JS engine (same screens, same rules)
- Show persistent banner: "Playing offline — will sync when back online"
- When `navigator.onLine` fires or next API call succeeds:
  - Sync all offline rounds to server via existing import endpoint
  - Switch back to server mode
  - Show "Synced ✓" banner for 3s

### Must — State Transfer (Server → Local)
- Read current game from last successful `GET /api/game/{id}` response (already in `state.game`)
- Read current round's bids from last `GET /api/game/{id}/bids` (if bidding phase)
- Create local game in IndexedDB with `linked_room` = playground share_code
- Mark as `sync_pending = true`
- Set `client_game_id` for dedup on sync-back

### Must — Sync Back (Local → Server)
- Use existing `POST /api/game/{share_code}/import` endpoint
- Import includes all rounds played offline
- Server re-derives scores (validation)
- Idempotent via `client_game_id`

### Must Not
- Don't switch to offline mode for non-game screens (home, stats, lobby)
- Don't lose any scored rounds — offline rounds must sync back
- Don't create duplicate games on sync-back (idempotency via client_game_id)

## UI

### Reconnecting Banner [ui]
- Position: fixed top, full width, above game content
- Style: yellow/amber background, "Reconnecting..." text with spinner
- Appears during retry attempts on game screens (bid/, roundend/), disappears on success
- Test: Playwright — block API mid-game → amber banner appears → unblock → banner disappears

### Offline Mode Banner [ui]
- Position: fixed top, full width
- Style: orange background, "Playing offline — will sync when back online"
- Persistent while in offline mode on game screens only
- Test: Playwright — exhaust retries mid-game → orange banner appears → game continues locally

### Sync UI Rules [ui]
- **No global sync banners.** No sync-related UI on home screen, stats, or any non-lobby screen.
- **No startup sync UI.** Background sync runs silently on startup and online events — zero UI.
- **Sync UI is lobby-only.** All sync feedback lives inside the room lobby.
- **Lobby sync button:** On lobby mount, silently check IDB for `sync_pending === true` games for this room. If pending games exist → show "Sync now" button (no banner, no message — just the button). If no pending games → no button, no UI.
- **Feedback only after user action.** User clicks "Sync now" → sync runs → show result inline ("3 games synced" or "1 failed. Retry?"). Feedback disappears after 3s on full success.
- Test: Playwright — lobby with pending games shows Sync button → click → result shown → button hidden after sync

## Data Requirements

No new API endpoints. No database changes. Uses existing:
- `state.game` (in-memory game state from last successful fetch)
- IndexedDB store (existing Quick Game infrastructure)
- `POST /api/game/{share_code}/import` (existing sync endpoint)

## Constraints

- Works with 2-8 players
- Handles mid-round failover (e.g., 3 of 5 bids submitted → offline takes over for remaining 2)
- Must work on mobile browsers (iOS Safari, Chrome Android)
- No service worker changes needed — this is app-level, not SW-level

## Non-Goals

- No offline support for stats/insights (read-only, needs server)
- No offline room creation (needs server for PIN hashing + share code)
- No conflict resolution for concurrent edits (single phone scorekeeper)
- No background sync via SW push events
