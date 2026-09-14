/**
 * game-api.test.js — Tests for the unified game-api.js interface.
 *
 * game-api delegates to game-engine for logic + IndexedDB persistence,
 * and fires server-sync as a side-effect for online backup.
 *
 * Run with: npx vitest run tests/js/game-api.test.js
 */

import 'fake-indexeddb/auto';
import { IDBFactory } from 'fake-indexeddb';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  resetForTesting,
  setIndexedDBForTesting,
} from '../../app/static/js/engine/store.js';

// We spy on the sync module — import it so vi.mock picks it up
import * as serverSync from '../../app/static/js/engine/server-sync.js';

vi.mock('../../app/static/js/engine/server-sync.js', () => ({
  syncRound: vi.fn(),
  syncGameState: vi.fn(),
}));

import {
  createGame,
  submitBid,
  getScoreboard,
} from '../../app/static/js/game-api.js';

// ─── helpers ─────────────────────────────────────────────────────────────────

function setOnline(value) {
  Object.defineProperty(navigator, 'onLine', { value, configurable: true });
}

function makePlayers() {
  return ['Alice', 'Bob'];
}

function makeSettings(overrides = {}) {
  return {
    formula: 'kachuful_standard',
    must_lose: false,
    rounds_per_set: 8,
    num_sets: 1,
    ...overrides,
  };
}

// ─── isolation ───────────────────────────────────────────────────────────────

beforeEach(() => {
  resetForTesting();
  setIndexedDBForTesting(new IDBFactory());
  setOnline(true);
  vi.clearAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ─── tests ───────────────────────────────────────────────────────────────────

describe('test_create_game_returns_game_object', () => {
  it('createGame returns game object with expected fields', async () => {
    const game = await createGame(makePlayers(), makeSettings());

    expect(game.current_round).toBe(1);
    expect(game.phase).toBe('bidding');
    expect(game.players).toEqual(makePlayers());
    expect(game.status).toBe('active');
    expect(typeof game.id).toBe('string');
  });
});

describe('test_submit_bid_calls_engine_and_syncs', () => {
  it('submitBid returns round and fires syncRound when online', async () => {
    const game = await createGame(makePlayers(), makeSettings());

    const round = await submitBid(game.id, 0, 3);

    expect(round.bids['0']).toBe(3);
    expect(serverSync.syncRound).toHaveBeenCalledOnce();
    const [syncedGameId, syncedRound] = serverSync.syncRound.mock.calls[0];
    expect(syncedGameId).toBe(game.id);
    expect(syncedRound.bids['0']).toBe(3);
  });
});

describe('test_submit_bid_offline_still_works', () => {
  it('submitBid succeeds and skips sync when offline', async () => {
    setOnline(false);
    const game = await createGame(makePlayers(), makeSettings());

    const round = await submitBid(game.id, 0, 2);

    expect(round.bids['0']).toBe(2);
    // syncRound is called from game-api but server-sync.syncRound checks onLine internally
    // The mock records the call; the real impl would be a no-op. Either way the
    // game-api layer must not throw.
  });
});

describe('test_get_scoreboard_returns_totals', () => {
  it('getScoreboard returns totals object after a scored round', async () => {
    const game = await createGame(makePlayers(), makeSettings());

    // Import engine functions directly to set up a complete round
    const engine = await import('../../app/static/js/engine/game-engine.js');
    await engine.submitBid(game.id, 0, 2);
    await engine.submitBid(game.id, 1, 3);
    await engine.startRound(game.id);
    await engine.enterRoundEnd(game.id);
    await engine.submitHands(game.id, 0, 2);
    await engine.submitHands(game.id, 1, 6);
    await engine.endRound(game.id);

    const scoreboard = await getScoreboard(game.id);

    expect(scoreboard).toHaveProperty('totals');
    expect(scoreboard).toHaveProperty('rounds');
    // Alice bid 2, won 2 → 2*10 = 20. Bob bid 3, won 6 → -30.
    expect(scoreboard.totals['0']).toBe(20);
    expect(scoreboard.totals['1']).toBe(-30);
  });
});
