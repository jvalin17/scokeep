/**
 * server-sync.test.js — Tests for the fire-and-forget server sync client.
 *
 * fetch is mocked via vitest. navigator.onLine is controlled per test.
 * Run with: npx vitest run tests/js/server-sync.test.js
 */

import 'fake-indexeddb/auto';
import { IDBFactory } from 'fake-indexeddb';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { syncRound, syncGameState, retrySyncQueue } from '../../app/static/js/engine/server-sync.js';
import { resetForTesting, setIndexedDBForTesting } from '../../app/static/js/engine/store.js';
import { getSyncQueue } from '../../app/static/js/engine/store.js';

// ─── helpers ─────────────────────────────────────────────────────────────────

function makeFetchSpy(ok = true) {
  const spy = vi.fn(() => Promise.resolve({ ok }));
  vi.stubGlobal('fetch', spy);
  return spy;
}

function setOnline(value) {
  Object.defineProperty(navigator, 'onLine', { value, configurable: true });
}

// ─── setup / teardown ────────────────────────────────────────────────────────

beforeEach(() => {
  resetForTesting();
  setIndexedDBForTesting(new IDBFactory());
  setOnline(true);
  vi.restoreAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ─── syncRound ───────────────────────────────────────────────────────────────

describe('test_sync_round_sends_correct_payload', () => {
  it('sends POST to /api/game/{id}/sync-round with the round as JSON body', async () => {
    const fetchSpy = makeFetchSpy();
    const round = {
      round_num: 1,
      cards_dealt: 8,
      trump_suit: 'spades',
      bids: { '0': 2, '1': 3 },
      hands_won: { '0': 2, '1': 3 },
      scores: { '0': 20, '1': 30 },
      status: 'scored',
    };

    syncRound('42', round);

    // fire-and-forget: give the microtask queue a tick to flush
    await Promise.resolve();

    expect(fetchSpy).toHaveBeenCalledOnce();
    const [url, options] = fetchSpy.mock.calls[0];
    expect(url).toBe('/api/game/42/sync-round');
    expect(options.method).toBe('POST');
    expect(options.credentials).toBe('same-origin');
    expect(options.headers['Content-Type']).toBe('application/json');
    expect(JSON.parse(options.body)).toEqual(round);
  });
});

describe('test_sync_round_silent_on_network_error', () => {
  it('does not propagate error when fetch rejects', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('network down'))));

    // Must not throw
    expect(() => syncRound('1', { round_num: 1 })).not.toThrow();

    // Wait for the rejected promise to settle — no unhandled rejection
    await new Promise((resolve) => setTimeout(resolve, 10));
  });
});

describe('test_sync_round_skipped_when_offline', () => {
  it('does not call fetch when navigator.onLine is false', async () => {
    setOnline(false);
    const fetchSpy = makeFetchSpy();

    syncRound('1', { round_num: 1 });
    await Promise.resolve();

    expect(fetchSpy).not.toHaveBeenCalled();
  });
});

describe('test_sync_round_skips_local_game_ids', () => {
  it('does not call fetch when gameId starts with "game-" (local Quick Game)', async () => {
    const fetchSpy = makeFetchSpy();
    const round = { round_num: 1, bids: { '0': 2 }, hands_won: { '0': 2 }, scores: { '0': 20 }, status: 'complete' };

    syncRound('game-1790064782456-z3is1lp', round);
    await Promise.resolve();

    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('still calls fetch for server game IDs (numeric)', async () => {
    const fetchSpy = makeFetchSpy();
    const round = { round_num: 1, bids: { '0': 2 }, hands_won: { '0': 2 }, scores: { '0': 20 }, status: 'complete' };

    syncRound(42, round);
    await Promise.resolve();

    expect(fetchSpy).toHaveBeenCalledOnce();
  });

  it('still calls fetch for server game IDs (numeric string)', async () => {
    const fetchSpy = makeFetchSpy();
    const round = { round_num: 1, bids: { '0': 2 }, hands_won: { '0': 2 }, scores: { '0': 20 }, status: 'complete' };

    syncRound('42', round);
    await Promise.resolve();

    expect(fetchSpy).toHaveBeenCalledOnce();
  });
});

// ─── syncGameState ────────────────────────────────────────────────────────────

describe('test_sync_game_state_sends_correct_payload', () => {
  it('sends POST to /api/game/{id}/sync-state with phase/round/dealer/status', async () => {
    const fetchSpy = makeFetchSpy();
    const game = {
      phase: 'playing',
      current_round: 2,
      dealer_index: 1,
      status: 'active',
    };

    syncGameState('99', game);
    await Promise.resolve();

    expect(fetchSpy).toHaveBeenCalledOnce();
    const [url, options] = fetchSpy.mock.calls[0];
    expect(url).toBe('/api/game/99/sync-state');
    expect(options.method).toBe('POST');
    const body = JSON.parse(options.body);
    expect(body.phase).toBe('playing');
    expect(body.current_round).toBe(2);
    expect(body.dealer_index).toBe(1);
    expect(body.status).toBe('active');
  });
});

describe('test_sync_game_state_skipped_when_offline', () => {
  it('does not call fetch when navigator.onLine is false', async () => {
    setOnline(false);
    const fetchSpy = makeFetchSpy();

    syncGameState('1', { phase: 'bidding', current_round: 1, dealer_index: 0, status: 'active' });
    await Promise.resolve();

    expect(fetchSpy).not.toHaveBeenCalled();
  });
});

describe('test_sync_game_state_skips_local_game_ids', () => {
  it('does not call fetch when gameId starts with "game-" (local Quick Game)', async () => {
    const fetchSpy = makeFetchSpy();
    const game = { phase: 'bidding', current_round: 1, dealer_index: 0, status: 'active' };

    syncGameState('game-1790064782456-z3is1lp', game);
    await Promise.resolve();

    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('still calls fetch for server game IDs (numeric)', async () => {
    const fetchSpy = makeFetchSpy();
    const game = { phase: 'bidding', current_round: 1, dealer_index: 0, status: 'active' };

    syncGameState(42, game);
    await Promise.resolve();

    expect(fetchSpy).toHaveBeenCalledOnce();
  });
});

// ─── sync queue (H6) ────────────────────────────────────────────────────────

describe('test_sync_round_queues_on_failure', () => {
  it('saves round to sync_queue when fetch fails', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('network down'))));

    const round = { round_num: 3, bids: { '0': 2 }, hands_won: { '0': 2 } };
    syncRound('42', round);

    // Wait for the async queue write
    await new Promise(r => setTimeout(r, 50));

    const queue = await getSyncQueue();
    expect(queue.length).toBe(1);
    expect(queue[0].game_id).toBe('42');
    expect(queue[0].round.round_num).toBe(3);
  });
});

describe('test_sync_round_retries_queued_rounds', () => {
  it('retries queued rounds and removes them on success', async () => {
    // First call fails (queues), then retry succeeds
    vi.stubGlobal('fetch', vi.fn()
      .mockRejectedValueOnce(new Error('network down'))
      .mockResolvedValueOnce({ ok: true }));

    const round = { round_num: 1, bids: { '0': 1 }, hands_won: { '0': 1 } };
    syncRound('10', round);
    await new Promise(r => setTimeout(r, 50));

    // Queue should have 1 item
    let queue = await getSyncQueue();
    expect(queue.length).toBe(1);

    // Now retry — fetch mock returns ok
    await retrySyncQueue();

    queue = await getSyncQueue();
    expect(queue.length).toBe(0);
  });
});
