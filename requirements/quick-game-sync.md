# Requirements: Quick Game → Room Sync

> Status: FINAL (reviewed by Security, Architect, QA roles)
> Priority: Next feature
> Capacitor-compatible: Yes — Web Crypto API + IndexedDB work in WebView

## Problem Statement

Quick Game data lives only in IndexedDB. Users who play offline with their regular group want those games to count toward room stats, insights, and career awards — without needing internet during the game.

## Two Quick Game Modes

### Mode 1: Quick Game (no room)
- Enter player names manually, pick settings, play, see results
- Data stays in IndexedDB only — never syncs
- No room, no PIN, no server interaction
- **No changes needed** — works today

### Mode 2: Quick Game (room mode)
- Pick a room from cached list → enter PIN → verify locally → play offline → sync later
- Game data syncs to server when device goes online

## Room Mode — Detailed Flow

### Step 1: Room Cache (online → IndexedDB)
| What | How |
|------|-----|
| When to cache | After successful online auth (`POST /api/playground/auth` returns 200) |
| What to cache | Room name, share_code, player list |
| PIN verifier | Computed **client-side** after auth: `PBKDF2(pin, random_salt, 600000)` → store `{salt, hash, iterations}` |
| IndexedDB store | New `rooms` object store in `scokeep-local` (keyPath: `share_code`) |
| Staleness | Room data refreshed each time user auths online. Offline: use cached data |
| Scope | Only rooms the user has previously joined on this device — NOT all rooms |

### Step 2: Room Selection in Quick Game
| What | How |
|------|-----|
| UI | Quick Game tab shows "Room" dropdown with cached rooms + "No Room" default |
| Room picked | Show PIN input field |
| PIN verification | Run PBKDF2 client-side with same params → compare hash. Uses Web Crypto API (built-in, no dependencies) |
| Rate limiting | 5 free attempts. After that, exponential lockout: 1, 2, 4, 8, 16, 32, 60 min. Counter stored in IndexedDB per room |
| On match | Player names auto-fill from room's cached player list. Game stores `linked_room: share_code` |
| On mismatch | Show error "Wrong PIN". PIN input clears. Room stays selected. User can retry (subject to rate limit) |
| Empty player list | Fall back to manual name entry |
| No room picked | Normal Quick Game (Mode 1) — no PIN, no sync |

### Step 3: Play Offline
- Same as today — game engine runs locally, data in IndexedDB
- Game object has extra fields:
  - `client_game_id`: UUIDv4 generated at creation time (for duplicate detection)
  - `linked_room`: `share_code` string or `null`
  - `sync_pending`: `true` (if linked) or `false`

### Step 4: Auto-Sync on Game Finish [backend]
| What | How |
|------|-----|
| Trigger | `confirmFinal` completes AND `navigator.onLine === true` AND `linked_room !== null` |
| Action | Immediately POST game + rounds to `POST /api/game/{share_code}/import` |
| Auth | Requires active session cookie for that room (user must have authed online before) |
| On success | Mark `sync_pending = false` in IndexedDB |
| On failure | Keep `sync_pending = true`. **Silent — no UI feedback.** User sees Sync button in lobby later |
| Test: vitest | Mock fetch → confirmFinal → assert sync_pending flipped on success, unchanged on failure |

### Step 5: Sync Button in Lobby [ui]
| What | How |
|------|-----|
| Trigger | User enters room lobby → silently check IDB for games with `sync_pending === true` AND `linked_room === this_room_share_code` |
| UI (pending exists) | Show "Sync now" button only. No banner. No count message. Just the button. |
| UI (no pending) | No button. No UI. Nothing. |
| User clicks "Sync now" | Sync runs → show result inline: "3 games synced" or "1 failed. Retry?" |
| Progress | "Syncing 1 of 3..." → "Syncing 2 of 3..." → "All synced!" |
| Partial failure | Already-synced games stay synced. Failed game shows specific error. |
| On full success | Result message disappears after 3s. Button hidden. `compute_insights()` triggered server-side |
| Test: Playwright | Lobby with pending → button visible → click → result shown → button hidden after sync |

### Step 6: Visual Indicator [ui]
| What | How |
|------|-----|
| Quick Game tab | Badge showing count of pending-sync games: "2 pending" |
| Purpose | User awareness — if they see this before clearing browser data, they know to sync first |
| Test: Playwright | Create linked Quick Game → Quick Game tab shows badge count |

### Sync UI Constraints [ui]
- **NO global banners for sync status.** No sync UI on home, stats, or any non-lobby screen.
- **NO startup sync UI.** Background sync on app startup is silent — zero UI. Data syncs for integrity only.
- **NO auto-showing banners.** All sync feedback is user-initiated (click "Sync now").
- **Gameplay banners (reconnecting/offline) are separate.** Those stay on game screens during active play — they are gameplay UX, not sync UI.

## Server Endpoint: POST /api/game/{share_code}/import

```
Auth: session cookie (user must have entered room online via PIN)
Server validates: session playground_id matches share_code's playground

Request:
{
  "client_game_id": "550e8400-e29b-41d4-a716-446655440000",
  "started_at": "2026-09-15T10:00:00.000Z",
  "finished_at": "2026-09-15T10:30:00.000Z",
  "players": ["Anjum", "Masood", "Lala"],
  "settings": { "mode": "rookie", "scoring_formula": "kachuful_standard", ... },
  "rounds": [
    {
      "round_num": 1,
      "bids": {"0": 2, "1": 1, "2": 0},
      "hands_won": {"0": 2, "1": 1, "2": 0},
      "cards_dealt": 8,
      "trump_suit": "spades"
    },
    ...
  ]
}

Server processing:
1. Check client_game_id — if exists, return 200 with existing game (idempotent)
2. Validate players are plausible for this room
3. Re-derive scores from bids + hands_won using scoring engine
4. Create Game + Round records in one transaction
5. Tag game with source: "offline_import"
6. Trigger compute_insights() (fire-and-forget — failure doesn't rollback)

Response (success):    200 { "game_id": 42, "rounds_imported": 8 }
Response (duplicate):  200 { "game_id": 42, "rounds_imported": 8, "already_existed": true }
Response (no auth):    401 { "detail": "Not authenticated" }
Response (validation): 422 { "detail": "Score mismatch in round 3" }
```

## Duplicate Detection
| Mechanism | Detail |
|-----------|--------|
| Primary key | `client_game_id` (UUIDv4) generated client-side at game creation |
| Server storage | New `client_game_id` column on Game table (VARCHAR(36), unique, nullable) |
| On duplicate | Return 200 with existing game — idempotent, not an error |
| Schema migration | `ALTER TABLE game ADD COLUMN client_game_id VARCHAR(36) UNIQUE` |

## DB Conflict Handling
| Scenario | Resolution |
|----------|-----------|
| Online games played between offline game and sync | No conflict — offline games INSERT as new records with their original timestamps |
| Multiple offline games pending | Each syncs individually. If one fails, others still sync |
| Same game synced twice (retry) | `client_game_id` dedup returns 200 — treated as success |
| Player list changed since offline game | Sync anyway — game was played with those players at that time |

## Security

| Concern | Mitigation |
|---------|-----------|
| PIN stored in IndexedDB | NOT stored. PBKDF2 verifier stored (salt + hash). Raw PIN never persisted |
| 4-digit PIN brute-force | PBKDF2 with 600K iterations — ~1 hour to exhaust 10K PINs in browser. Client-side rate limiter locks after 5 attempts |
| PIN hash exposed via API | NOT exposed. pin_hash is NOT in browse endpoint response. Verifier computed client-side after successful online auth |
| Client-side PIN check bypass | PIN check is UX gate only. Real security is server-side: import endpoint requires valid session cookie (PIN verified by server at room entry) |
| Tampered game data | Server re-derives scores from bids + hands_won. Rejects mismatches |
| Fabricated games | Rate limit imports (max 10 per room per day). Reject timestamps older than 30 days. Tag with `source: "offline_import"` for audit |
| IndexedDB data extraction | Attacker with disk access can read IDB files but cannot brute-force PIN verifier without browser context (PBKDF2 is slow). Same-origin JS attacker faces rate limiter |

## IndexedDB Schema Changes

### Version 2 Migration
```js
const DB_VERSION = 2;

request.onupgradeneeded = (event) => {
  const db = event.target.result;
  const oldVersion = event.oldVersion;

  if (oldVersion < 1) {
    db.createObjectStore('games', { keyPath: 'id' });
    const rounds = db.createObjectStore('rounds', { keyPath: ['game_id', 'round_num'] });
    rounds.createIndex('game_id', 'game_id');
  }
  if (oldVersion < 2) {
    db.createObjectStore('rooms', { keyPath: 'share_code' });
  }
};
```

### Room Store Schema
```js
{
  share_code: "KLCC",           // keyPath
  name: "Besties",
  players: ["Masood", "Afeefa", "Jj"],
  pin_verifier: {
    salt: "a1b2c3...",          // 16 bytes hex
    hash: "d4e5f6...",          // 32 bytes hex
    iterations: 600000
  },
  attempts: 0,                  // rate limiter counter
  locked_until: null,           // lockout timestamp
  cached_at: "2026-09-16T..."   // when this room was last cached
}
```

### Game Object New Fields
```js
{
  // ... existing fields ...
  client_game_id: "550e8400-...",     // UUIDv4, set at creation
  linked_room: "KLCC",               // share_code or null
  sync_pending: true                  // true if linked and not yet synced
}
```

## New Dependencies
None. PBKDF2 uses built-in Web Crypto API (`crypto.subtle.deriveBits`).

## What Changes

| Component | Change |
|-----------|--------|
| IndexedDB schema (store.js) | Bump to v2, add `rooms` store, add `client_game_id` / `linked_room` / `sync_pending` fields to games |
| Quick Game tab (home.js) | Room dropdown + PIN input + auto-fill players |
| game-engine.js | Generate `client_game_id` (UUIDv4) at game creation |
| game-api.js | Auto-sync on `confirmFinal` when online + linked |
| Lobby screen (lobby.js) | Sync banner, progress UI, check for pending games |
| Auth flow (home.js Join tab) | After successful auth, cache room + compute PBKDF2 verifier |
| Server: new endpoint | `POST /api/game/{share_code}/import` |
| Server: Game model | New `client_game_id` column (nullable, unique) |
| Server: Game model | New `source` column or tag for "offline_import" |
| SW cache (sw.js) | No new deps — Web Crypto is built-in |

## What Does NOT Change
- Online game flow (unchanged)
- Quick Game Mode 1 / no room (unchanged)
- ML pipeline (unchanged — receives more data via import, recomputes insights)
- Scoring engine (unchanged — server reuses existing scoring for validation)
- Game screens (bidding, play, roundend, scoreboard — unchanged)
- Browse endpoint (unchanged — does NOT expose pin_hash)

## Out of Scope (v1)
- Cross-device sync (only same device that played the Quick Game can sync)
- Background Sync API (auto-sync on finish + lobby banner is sufficient)
- Creating rooms offline (rooms are online-only)
- Syncing Mode 1 Quick Games (no room = no sync, ever)
- `beforeunload` warning for unsynced data (doesn't work on mobile)
- Export-to-file backup (too much friction for the use case)

## Test Requirements
| Test | Type | What it verifies |
|------|------|------------------|
| PBKDF2 PIN verification | Vitest | Correct PIN → match, wrong PIN → no match, rate limiter locks after 5 attempts |
| Room cache on auth | Playwright | Join room online → room appears in Quick Game dropdown |
| Quick Game with room | Playwright | Pick room → enter PIN → players auto-fill → game plays |
| Auto-sync on finish | Playwright | Finish linked game while online → `sync_pending` becomes false |
| Lobby sync banner | Playwright | Enter room with pending games → banner shows count → sync clears them |
| Import endpoint | pytest | Create game + rounds, re-derive scores, duplicate detection, auth check |
| IDB v1→v2 migration | Vitest | Open v1 DB with data → reopen v2 → data intact + rooms store exists |
| Partial sync failure | Playwright | 3 games pending, network drops after 2 → 2 synced, 1 still pending |
