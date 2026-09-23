/**
 * sync-manager.test.js — Unit tests for SyncManager (IDB-first sync).
 *
 * Fixtures are synthetic (factory), matching sync-import / sync-back test shapes.
 * Run with: npx vitest run tests/js/sync-manager.test.js
 */

import 'fake-indexeddb/auto';
import { IDBFactory } from 'fake-indexeddb';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  saveGame,
  saveRound,
  getGame,
  getRound,
  getSyncQueue,
  saveSyncQueueItem,
  resetForTesting,
  setIndexedDBForTesting,
} from '../../app/static/js/engine/store.js';
import { logger } from '../../app/static/js/components/logger.js';
import {
  syncManager,
  isLocalId,
} from '../../app/static/js/engine/sync-manager.js';

function setOnline(value) {
  Object.defineProperty(navigator, 'onLine', { value, configurable: true });
}

function makeRound(overrides = {}) {
  return {
    game_id: 42,
    round_num: 1,
    cards_dealt: 8,
    trump_suit: 'spades',
    bids: { '0': 2, '1': 3 },
    hands_won: { '0': 2, '1': 3 },
    scores: { '0': 20, '1': 30 },
    status: 'complete',
    synced: false,
    ...overrides,
  };
}

function makeLinkedGame(overrides = {}) {
  return {
    id: 'game-1726400000-abc',
    client_game_id: 'game-1726400000-abc',
    linked_room: 'KLCC',
    sync_pending: true,
    players: ['Anjum', 'Masood', 'Lala'],
    settings: {
      mode: 'rookie',
      scoring_formula: 'kachuful_standard',
      must_lose: true,
      rounds_per_set: 8,
      num_sets: 1,
    },
    current_round: 1,
    total_rounds: 8,
    phase: 'final',
    dealer_index: 0,
    status: 'finished',
    started_at: '2026-09-15T10:00:00.000Z',
    finished_at: '2026-09-15T10:30:00.000Z',
    ...overrides,
  };
}

beforeEach(() => {
  resetForTesting();
  setIndexedDBForTesting(new IDBFactory());
  setOnline(true);
  syncManager.resetForTesting();
  vi.restoreAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('test_is_local_id', () => {
  it('returns true for local game- prefix ids', () => {
    expect(isLocalId('game-xxx')).toBe(true);
  });

  it('returns false for numeric string ids', () => {
    expect(isLocalId('42')).toBe(false);
  });

  it('returns false for numeric ids', () => {
    expect(isLocalId(42)).toBe(false);
  });
});

describe('test_sync_round_posts_correct_payload', () => {
  it('POSTs the round to /api/game/{id}/sync-round and marks synced', async () => {
    const fetchSpy = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    vi.stubGlobal('fetch', fetchSpy);
    const round = makeRound({ round_num: 3 });
    await saveRound(round);

    const result = await syncManager.syncRound(42, round);

    expect(fetchSpy).toHaveBeenCalledOnce();
    const [url, options] = fetchSpy.mock.calls[0];
    expect(url).toBe('/api/game/42/sync-round');
    expect(options.method).toBe('POST');
    expect(options.credentials).toBe('same-origin');
    expect(options.headers['Content-Type']).toBe('application/json');
    expect(JSON.parse(options.body).round_num).toBe(3);
    expect(result.success).toBe(true);
    expect(round.synced).toBe(true);
    const stored = await getRound(42, 3);
    expect(stored.synced).toBe(true);
  });
});

describe('test_sync_round_queues_on_failure', () => {
  it('queues the round in IDB when fetch returns 500', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    const round = makeRound({ round_num: 4 });

    const result = await syncManager.syncRound(42, round);

    expect(result.success).toBe(false);
    expect(result.status).toBe(500);
    const queue = await getSyncQueue();
    expect(queue).toHaveLength(1);
    expect(queue[0].game_id).toBe(42);
    expect(queue[0].round.round_num).toBe(4);
  });
});

describe('test_sync_round_skips_when_offline', () => {
  it('does not fetch and queues the round when offline', async () => {
    setOnline(false);
    const fetchSpy = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    vi.stubGlobal('fetch', fetchSpy);
    const round = makeRound({ round_num: 5 });

    const result = await syncManager.syncRound(42, round);

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(result).toEqual({ success: false, reason: 'offline' });
    const queue = await getSyncQueue();
    expect(queue).toHaveLength(1);
    expect(queue[0].round.round_num).toBe(5);
  });
});

describe('test_sync_round_logs_on_success', () => {
  it('logs info with category sync on successful round sync', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200 }));
    const infoSpy = vi.spyOn(logger, 'info');
    const round = makeRound();
    await saveRound(round);

    await syncManager.syncRound(42, round);

    expect(infoSpy).toHaveBeenCalledWith('sync', expect.stringMatching(/syncRound/));
  });
});

describe('test_sync_round_logs_on_failure', () => {
  it('logs warn with category sync when round sync fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    const warnSpy = vi.spyOn(logger, 'warn');
    const round = makeRound({ round_num: 6 });

    await syncManager.syncRound(42, round);

    expect(warnSpy).toHaveBeenCalledWith('sync', expect.stringMatching(/syncRound/));
  });
});

describe('test_sync_game_posts_all_rounds', () => {
  it('POSTs a payload containing all stored rounds', async () => {
    const game = makeLinkedGame();
    await saveGame(game);
    await saveRound(makeRound({ game_id: game.id, round_num: 1 }));
    await saveRound(makeRound({ game_id: game.id, round_num: 2 }));
    await saveRound(makeRound({ game_id: game.id, round_num: 3 }));

    const fetchSpy = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    vi.stubGlobal('fetch', fetchSpy);

    const result = await syncManager.syncGame(game);

    expect(result.success).toBe(true);
    const [url, options] = fetchSpy.mock.calls[0];
    expect(url).toBe('/api/game/KLCC/import');
    const body = JSON.parse(options.body);
    expect(body.rounds).toHaveLength(3);
    expect(body.rounds.map((round) => round.round_num)).toEqual([1, 2, 3]);
    expect(body.client_game_id).toBe(game.client_game_id);
  });
});

describe('test_sync_game_sets_sync_pending_false', () => {
  it('clears sync_pending in IDB after a successful import', async () => {
    const game = makeLinkedGame();
    await saveGame(game);
    await saveRound(makeRound({ game_id: game.id, round_num: 1 }));
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200 }));

    await syncManager.syncGame(game);

    const updated = await getGame(game.id);
    expect(updated.sync_pending).toBe(false);
  });
});

describe('test_sync_game_returns_status_on_error', () => {
  it('returns status 422 and leaves sync_pending true', async () => {
    const game = makeLinkedGame();
    await saveGame(game);
    await saveRound(makeRound({ game_id: game.id, round_num: 1 }));
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 422 }));

    const result = await syncManager.syncGame(game);

    expect(result.success).toBe(false);
    expect(result.status).toBe(422);
    const updated = await getGame(game.id);
    expect(updated.sync_pending).toBe(true);
  });
});

describe('test_sync_pending_probes_health', () => {
  it('issues GET /api/health before importing pending games', async () => {
    const game = makeLinkedGame();
    await saveGame(game);
    await saveRound(makeRound({ game_id: game.id, round_num: 1 }));

    const fetchSpy = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200 })
      .mockResolvedValueOnce({ ok: true, status: 200 });
    vi.stubGlobal('fetch', fetchSpy);

    await syncManager.syncPending();

    expect(fetchSpy.mock.calls[0][0]).toBe('/api/health');
    expect(fetchSpy.mock.calls[0][1].credentials).toBe('same-origin');
  });
});

describe('test_sync_pending_handles_4xx_vs_5xx', () => {
  it('marks 422 as sync_failed and continues; stops on 500', async () => {
    const game422 = makeLinkedGame({
      id: 'game-422',
      client_game_id: 'game-422',
    });
    const game500 = makeLinkedGame({
      id: 'game-500',
      client_game_id: 'game-500',
      started_at: '2026-09-15T09:00:00.000Z',
    });
    const gameOk = makeLinkedGame({
      id: 'game-ok',
      client_game_id: 'game-ok',
      started_at: '2026-09-15T08:00:00.000Z',
    });
    await saveGame(game422);
    await saveGame(game500);
    await saveGame(gameOk);
    await saveRound(makeRound({ game_id: game422.id, round_num: 1 }));
    await saveRound(makeRound({ game_id: game500.id, round_num: 1 }));
    await saveRound(makeRound({ game_id: gameOk.id, round_num: 1 }));

    const fetchSpy = vi.fn(async (url, options) => {
      if (url === '/api/health') return { ok: true, status: 200 };
      const parsed = JSON.parse(options.body);
      if (parsed.client_game_id === 'game-422') return { ok: false, status: 422 };
      if (parsed.client_game_id === 'game-500') return { ok: false, status: 500 };
      return { ok: true, status: 200 };
    });
    vi.stubGlobal('fetch', fetchSpy);

    const result = await syncManager.syncPending();

    const updated422 = await getGame(game422.id);
    expect(updated422.sync_pending).toBe(false);
    expect(updated422.sync_failed).toBe(true);

    const updated500 = await getGame(game500.id);
    expect(updated500.sync_pending).toBe(true);

    const updatedOk = await getGame(gameOk.id);
    expect(updatedOk.sync_pending).toBe(true);

    expect(result.failed).toBeGreaterThanOrEqual(1);
    const importCalls = fetchSpy.mock.calls.filter(([url]) => url !== '/api/health');
    expect(importCalls.length).toBe(2);
  });
});

describe('test_lock_prevents_overlapping', () => {
  it('starts the second syncRound only after the first fetch settles', async () => {
    let releaseFirst;
    const firstStarted = new Promise((resolve) => {
      const originalResolve = resolve;
      releaseFirst = null;
      vi.stubGlobal('fetch', vi.fn(() => new Promise((resolveFetch) => {
        if (!releaseFirst) {
          releaseFirst = () => resolveFetch({ ok: true, status: 200 });
          originalResolve();
        } else {
          resolveFetch({ ok: true, status: 200 });
        }
      })));
    });

    const firstRound = makeRound({ round_num: 1 });
    const secondRound = makeRound({ round_num: 2 });
    await saveRound(firstRound);
    await saveRound(secondRound);

    const firstPromise = syncManager.syncRound(42, firstRound);
    await firstStarted;
    const secondPromise = syncManager.syncRound(42, secondRound);

    expect(fetch).toHaveBeenCalledTimes(1);

    releaseFirst();
    await Promise.all([firstPromise, secondPromise]);
    expect(fetch).toHaveBeenCalledTimes(2);
  });
});

describe('test_lock_drains_three_overlapping', () => {
  it('runs three syncRounds strictly one at a time', async () => {
    let inFlight = 0;
    let maxInFlight = 0;
    const order = [];

    vi.stubGlobal('fetch', vi.fn(async (_url, options) => {
      inFlight++;
      maxInFlight = Math.max(maxInFlight, inFlight);
      const body = JSON.parse(options.body);
      order.push(body.round_num);
      await new Promise((resolve) => setTimeout(resolve, 20));
      inFlight--;
      return { ok: true, status: 200 };
    }));

    const rounds = [
      makeRound({ round_num: 1 }),
      makeRound({ round_num: 2 }),
      makeRound({ round_num: 3 }),
    ];
    for (const round of rounds) {
      await saveRound(round);
    }

    await Promise.all(rounds.map((round) => syncManager.syncRound(42, round)));

    expect(maxInFlight).toBe(1);
    expect(order).toEqual([1, 2, 3]);
    expect(fetch).toHaveBeenCalledTimes(3);
  });
});

describe('test_lock_queues_sync_game', () => {
  it('runs syncGame after an in-flight syncRound and both complete', async () => {
    const game = makeLinkedGame();
    await saveGame(game);
    await saveRound(makeRound({ game_id: game.id, round_num: 1 }));
    const round = makeRound({ round_num: 8 });
    await saveRound(round);

    let releaseRound;
    const roundStarted = new Promise((resolve) => {
      vi.stubGlobal('fetch', vi.fn((url) => new Promise((resolveFetch) => {
        if (String(url).includes('sync-round') && !releaseRound) {
          releaseRound = () => resolveFetch({ ok: true, status: 200 });
          resolve();
          return;
        }
        resolveFetch({ ok: true, status: 200 });
      })));
    });

    const roundPromise = syncManager.syncRound(42, round);
    await roundStarted;
    const gamePromise = syncManager.syncGame(game);

    expect(fetch.mock.calls.some(([url]) => String(url).includes('/import'))).toBe(false);

    releaseRound();
    const [roundResult, gameResult] = await Promise.all([roundPromise, gamePromise]);
    expect(roundResult.success).toBe(true);
    expect(gameResult.success).toBe(true);
    expect(fetch.mock.calls.some(([url]) => String(url).includes('/import'))).toBe(true);
  });
});

describe('test_retry_sync_queue', () => {
  it('retries queued rounds and deletes them on 200', async () => {
    await saveSyncQueueItem(42, makeRound({ round_num: 1 }));
    await saveSyncQueueItem(42, makeRound({ round_num: 2 }));
    const fetchSpy = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    vi.stubGlobal('fetch', fetchSpy);

    await syncManager.retrySyncQueue();

    expect(fetchSpy).toHaveBeenCalledTimes(2);
    expect(fetchSpy.mock.calls[0][0]).toBe('/api/game/42/sync-round');
    const queue = await getSyncQueue();
    expect(queue).toHaveLength(0);
  });
});
