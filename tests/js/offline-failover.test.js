/**
 * offline-failover.test.js — Tests for transferToOffline and isNetworkError.
 *
 * Uses fake-indexeddb for IDB operations.
 *
 * Run with: npx vitest run tests/js/offline-failover.test.js
 */

import 'fake-indexeddb/auto';
import { IDBFactory } from 'fake-indexeddb';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  resetForTesting,
  setIndexedDBForTesting,
  getGame,
  getRound,
} from '../../app/static/js/engine/store.js';
import {
  transferToOffline,
  isNetworkError,
} from '../../app/static/js/engine/offline-failover.js';
import { NetworkError } from '../../app/static/js/components/network-error.js';

// ─── setup ────────────────────────────────────────────────────────────────────

beforeEach(() => {
  resetForTesting();
  setIndexedDBForTesting(new IDBFactory());
});

// ─── helpers ──────────────────────────────────────────────────────────────────

function makeServerGame(overrides = {}) {
  return {
    id: 42,
    players: ['Alice', 'Bob', 'Carol'],
    settings: { variant: 'standard' },
    current_round: 3,
    total_rounds: 7,
    dealer_index: 2,
    phase: 'bidding',
    started_at: '2026-09-20T14:00:00Z',
    ...overrides,
  };
}

function makeRoundData(overrides = {}) {
  return {
    bids: { '0': 2, '1': 1 },
    round_num: 3,
    cards_dealt: 5,
    trump_suit: 'hearts',
    ...overrides,
  };
}

// ─── transferToOffline ────────────────────────────────────────────────────────

describe('test_transfer_to_offline_creates_local_game', () => {
  it('creates a valid local game in IDB', async () => {
    const serverGame = makeServerGame();
    const roundData = makeRoundData();

    const localId = await transferToOffline(serverGame, roundData, 'ABC123');

    expect(localId).toMatch(/^game-/);

    const savedGame = await getGame(localId);
    expect(savedGame).not.toBeNull();
    expect(savedGame.players).toEqual(['Alice', 'Bob', 'Carol']);
    expect(savedGame.settings).toEqual({ variant: 'standard' });
    expect(savedGame.current_round).toBe(3);
    expect(savedGame.total_rounds).toBe(7);
    expect(savedGame.phase).toBe('bidding');
    expect(savedGame.status).toBe('active');
    expect(savedGame.sync_pending).toBe(true);
    expect(savedGame.source).toBe('failover');
    expect(savedGame.client_game_id).toContain('failover-42-');
  });
});

describe('test_transfer_to_offline_preserves_round_data', () => {
  it('saves the current round data to IDB', async () => {
    const serverGame = makeServerGame();
    const roundData = makeRoundData();

    const localId = await transferToOffline(serverGame, roundData, 'ABC123');

    const savedRound = await getRound(localId, 3);
    expect(savedRound).not.toBeNull();
    expect(savedRound.bids).toEqual({ '0': 2, '1': 1 });
    expect(savedRound.cards_dealt).toBe(5);
    expect(savedRound.trump_suit).toBe('hearts');
  });
});

describe('test_transfer_to_offline_stores_linked_room', () => {
  it('sets linked_room from the share code', async () => {
    const serverGame = makeServerGame();
    const roundData = makeRoundData();

    const localId = await transferToOffline(serverGame, roundData, 'XYZ789');

    const savedGame = await getGame(localId);
    expect(savedGame.linked_room).toBe('XYZ789');
  });

  it('sets linked_room to null if no share code', async () => {
    const serverGame = makeServerGame();
    const roundData = makeRoundData();

    const localId = await transferToOffline(serverGame, roundData, null);

    const savedGame = await getGame(localId);
    expect(savedGame.linked_room).toBeNull();
  });
});

describe('test_transfer_to_offline_handles_idb_failure', () => {
  it('throws descriptive error when IDB is unavailable', async () => {
    // Break IDB by setting it to a factory that throws
    setIndexedDBForTesting({
      open: () => {
        const req = {};
        setTimeout(() => {
          if (req.onerror) req.onerror(new Error('IDB blocked'));
        }, 0);
        return req;
      },
    });
    resetForTesting();

    const serverGame = makeServerGame();
    const roundData = makeRoundData();

    await expect(transferToOffline(serverGame, roundData, 'ABC'))
      .rejects.toThrow(/Cannot play offline/);
  });
});

describe('test_transfer_to_offline_unique_ids', () => {
  it('generates unique IDs for each call', async () => {
    const serverGame = makeServerGame();
    const roundData = makeRoundData();

    const id1 = await transferToOffline(serverGame, roundData, 'A');
    const id2 = await transferToOffline(serverGame, { ...roundData, round_num: 4 }, 'A');

    expect(id1).not.toBe(id2);
  });
});

// ─── isNetworkError ───────────────────────────────────────────────────────────

describe('test_is_network_error_matches_network_error', () => {
  it('returns true for NetworkError instances', () => {
    expect(isNetworkError(new NetworkError('offline'))).toBe(true);
    expect(isNetworkError(new NetworkError('exhausted'))).toBe(true);
  });
});

describe('test_is_network_error_matches_abort_error', () => {
  it('returns true for AbortError (timeout)', () => {
    const err = new DOMException('Aborted', 'AbortError');
    expect(isNetworkError(err)).toBe(true);
  });
});

describe('test_is_network_error_matches_fetch_type_error', () => {
  it('returns true for TypeError with fetch in message', () => {
    expect(isNetworkError(new TypeError('Failed to fetch'))).toBe(true);
    expect(isNetworkError(new TypeError('NetworkError when attempting to fetch'))).toBe(true);
  });
});

describe('test_is_network_error_rejects_js_type_error', () => {
  it('returns false for regular TypeError (JS bug)', () => {
    expect(isNetworkError(new TypeError('Cannot read property x of undefined'))).toBe(false);
    expect(isNetworkError(new TypeError('null is not a function'))).toBe(false);
  });
});

describe('test_is_network_error_rejects_other_errors', () => {
  it('returns false for general errors', () => {
    expect(isNetworkError(new Error('Something went wrong'))).toBe(false);
    expect(isNetworkError(new RangeError('out of bounds'))).toBe(false);
  });
});
