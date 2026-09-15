/**
 * server-sync.test.js — Tests for the fire-and-forget server sync client.
 *
 * fetch is mocked via vitest. navigator.onLine is controlled per test.
 * Run with: npx vitest run tests/js/server-sync.test.js
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { syncRound, syncGameState } from '../../app/static/js/engine/server-sync.js';

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

    syncRound('game-42', round);

    // fire-and-forget: give the microtask queue a tick to flush
    await Promise.resolve();

    expect(fetchSpy).toHaveBeenCalledOnce();
    const [url, options] = fetchSpy.mock.calls[0];
    expect(url).toBe('/api/game/game-42/sync-round');
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
    expect(() => syncRound('game-1', { round_num: 1 })).not.toThrow();

    // Wait for the rejected promise to settle — no unhandled rejection
    await new Promise((resolve) => setTimeout(resolve, 10));
  });
});

describe('test_sync_round_skipped_when_offline', () => {
  it('does not call fetch when navigator.onLine is false', async () => {
    setOnline(false);
    const fetchSpy = makeFetchSpy();

    syncRound('game-1', { round_num: 1 });
    await Promise.resolve();

    expect(fetchSpy).not.toHaveBeenCalled();
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

    syncGameState('game-99', game);
    await Promise.resolve();

    expect(fetchSpy).toHaveBeenCalledOnce();
    const [url, options] = fetchSpy.mock.calls[0];
    expect(url).toBe('/api/game/game-99/sync-state');
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

    syncGameState('game-1', { phase: 'bidding', current_round: 1, dealer_index: 0, status: 'active' });
    await Promise.resolve();

    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
