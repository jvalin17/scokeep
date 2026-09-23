/**
 * game-api.test.js — Tests for the unified game-api.js interface.
 *
 * Fixtures are synthetic (factory), matching existing game-api / engine tests.
 * Run with: npx vitest run tests/js/game-api.test.js
 */

import 'fake-indexeddb/auto';
import { IDBFactory } from 'fake-indexeddb';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  resetForTesting,
  setIndexedDBForTesting,
  getGame,
} from '../../app/static/js/engine/store.js';
import { syncManager } from '../../app/static/js/engine/sync-manager.js';

vi.mock('../../app/static/js/engine/sync-manager.js', () => ({
  syncManager: {
    syncRound: vi.fn(),
    syncGame: vi.fn(() => Promise.resolve({ success: true })),
    retrySyncQueue: vi.fn(() => Promise.resolve()),
  },
  isLocalId: (gameId) => typeof gameId === 'string' && gameId.startsWith('game-'),
}));

import {
  createGame,
  createOnlineGame,
  submitBid,
  endRound,
  getScoreboard,
  confirmFinal,
  endGame,
} from '../../app/static/js/game-api.js';

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

beforeEach(() => {
  resetForTesting();
  setIndexedDBForTesting(new IDBFactory());
  setOnline(true);
  vi.clearAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
});

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

describe('test_create_online_game_sets_server_id', () => {
  it('stores server_game_id, linked_room, and sync_pending false', async () => {
    const game = await createOnlineGame(42, makePlayers(), makeSettings(), 'KLCC');

    expect(game.server_game_id).toBe(42);
    expect(game.linked_room).toBe('KLCC');
    expect(game.sync_pending).toBe(false);

    const stored = await getGame(game.id);
    expect(stored.server_game_id).toBe(42);
    expect(stored.linked_room).toBe('KLCC');
    expect(stored.sync_pending).toBe(false);
  });
});

describe('test_submit_bid_does_not_sync', () => {
  it('submitBid writes the bid and does not call syncRound', async () => {
    const game = await createGame(makePlayers(), makeSettings());

    const round = await submitBid(game.id, 0, 3);

    expect(round.bids['0']).toBe(3);
    expect(syncManager.syncRound).not.toHaveBeenCalled();
  });
});

describe('test_submit_bid_offline_still_works', () => {
  it('submitBid succeeds when offline', async () => {
    setOnline(false);
    const game = await createGame(makePlayers(), makeSettings());

    const round = await submitBid(game.id, 0, 2);

    expect(round.bids['0']).toBe(2);
    expect(syncManager.syncRound).not.toHaveBeenCalled();
  });
});

describe('test_end_round_syncs_server_game_id', () => {
  it('endRound syncs the completed round to the server game id', async () => {
    const game = await createOnlineGame(42, makePlayers(), makeSettings(), 'KLCC');
    const engine = await import('../../app/static/js/engine/game-engine.js');
    await engine.submitBid(game.id, 0, 2);
    await engine.submitBid(game.id, 1, 3);
    await engine.startRound(game.id);
    await engine.enterRoundEnd(game.id);
    await engine.submitHands(game.id, 0, 2);
    await engine.submitHands(game.id, 1, 6);

    const round = await endRound(game.id);

    expect(round.status).toBe('complete');
    expect(syncManager.syncRound).toHaveBeenCalledOnce();
    const [serverGameId, syncedRound] = syncManager.syncRound.mock.calls[0];
    expect(serverGameId).toBe(42);
    expect(syncedRound.round_num).toBe(1);
  });

  it('endRound does not sync when there is no server_game_id', async () => {
    const game = await createGame(makePlayers(), makeSettings());
    const engine = await import('../../app/static/js/engine/game-engine.js');
    await engine.submitBid(game.id, 0, 2);
    await engine.submitBid(game.id, 1, 3);
    await engine.startRound(game.id);
    await engine.enterRoundEnd(game.id);
    await engine.submitHands(game.id, 0, 2);
    await engine.submitHands(game.id, 1, 6);

    await endRound(game.id);

    expect(syncManager.syncRound).not.toHaveBeenCalled();
  });
});

describe('test_get_scoreboard_returns_totals', () => {
  it('getScoreboard returns totals object after a scored round', async () => {
    const game = await createGame(makePlayers(), makeSettings());

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
    expect(scoreboard.totals['0']).toBe(20);
    expect(scoreboard.totals['1']).toBe(-30);
  });
});

describe('test_confirm_final_ends_server_game', () => {
  it('POSTs /end then /confirm-final so the server game leaves active', async () => {
    const fetchSpy = vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 }));
    vi.stubGlobal('fetch', fetchSpy);

    const game = await createOnlineGame(42, makePlayers(), makeSettings(), 'KLCC');
    await endGame(game.id);

    await confirmFinal(game.id);
    await vi.waitFor(() => {
      expect(fetchSpy.mock.calls.length).toBeGreaterThanOrEqual(2);
    });

    expect(syncManager.retrySyncQueue).toHaveBeenCalledOnce();
    expect(syncManager.syncGame).not.toHaveBeenCalled();

    const urls = fetchSpy.mock.calls
      .filter(([, options]) => options?.method === 'POST')
      .map(([url]) => String(url));
    expect(urls).toContain('/api/game/42/end');
    expect(urls).toContain('/api/game/42/confirm-final');
  });

  it('marks server_end_pending when server finalize fails', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => {
      throw new Error('network down');
    }));

    const game = await createOnlineGame(42, makePlayers(), makeSettings(), 'KLCC');
    await endGame(game.id);

    await confirmFinal(game.id);
    await vi.waitFor(async () => {
      const stored = await getGame(game.id);
      expect(stored.server_end_pending).toBe(true);
    });
  });

  it('imports via syncGame for offline pending games without server_game_id', async () => {
    const game = await createGame(makePlayers(), {
      ...makeSettings(),
      linked_room: 'KLCC',
    });
    expect(game.sync_pending).toBe(true);
    expect(game.server_game_id).toBeUndefined();
    await endGame(game.id);

    await confirmFinal(game.id);

    expect(syncManager.syncGame).toHaveBeenCalledOnce();
  });
});
