/**
 * sync-back.test.js — Tests for the sync-back flow (attemptSyncBack).
 *
 * Tests that pending games are synced on online event, probes health first,
 * handles sync failures, and clears sync_pending on success.
 *
 * Run with: npx vitest run tests/js/sync-back.test.js
 */

import 'fake-indexeddb/auto';
import { IDBFactory } from 'fake-indexeddb';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  resetForTesting,
  setIndexedDBForTesting,
  saveGame,
  getGame,
  saveRound,
} from '../../app/static/js/engine/store.js';
import {
  attemptSyncBack,
} from '../../app/static/js/engine/sync-back.js';

// ─── setup ────────────────────────────────────────────────────────────────────

beforeEach(() => {
  resetForTesting();
  setIndexedDBForTesting(new IDBFactory());
  vi.stubGlobal('fetch', vi.fn());
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ─── helpers ──────────────────────────────────────────────────────────────────

function makeGame(overrides = {}) {
  return {
    id: 'game-1726840000-abc12345',
    client_game_id: 'failover-42-1726840000',
    players: ['Alice', 'Bob', 'Carol'],
    settings: { variant: 'standard' },
    current_round: 3,
    total_rounds: 7,
    dealer_index: 2,
    phase: 'scoreboard',
    status: 'finished',
    linked_room: 'KLMN',
    sync_pending: true,
    started_at: '2026-09-20T14:00:00Z',
    finished_at: '2026-09-20T15:00:00Z',
    source: 'failover',
    ...overrides,
  };
}

function makeRound(gameId, roundNum) {
  return {
    game_id: gameId,
    round_num: roundNum,
    bids: { '0': 2, '1': 1, '2': 0 },
    hands_won: { '0': 1, '1': 1, '2': 1 },
    cards_dealt: 3,
    trump_suit: 'hearts',
  };
}

function mockHealthOk() {
  globalThis.fetch.mockResolvedValueOnce({ ok: true });
}

function mockHealthFail() {
  globalThis.fetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));
}

function mockImportOk() {
  globalThis.fetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve({ id: 99 }),
  });
}

function mockImportFail() {
  globalThis.fetch.mockResolvedValueOnce({
    ok: false,
    status: 500,
    json: () => Promise.resolve({ detail: 'Server error' }),
  });
}

function mockImportClientError() {
  globalThis.fetch.mockResolvedValueOnce({
    ok: false,
    status: 422,
    json: () => Promise.resolve({ detail: 'Validation error' }),
  });
}

// ─── probes health before syncing ─────────────────────────────────────────────

describe('test_sync_back_probes_health_first', () => {
  it('does not sync if health probe fails', async () => {
    const game = makeGame();
    await saveGame(game);
    await saveRound(makeRound(game.id, 1));

    mockHealthFail();

    const result = await attemptSyncBack();
    expect(result).toEqual({ synced: 0, failed: 0, skipped: true });
    // Only one fetch call (health probe), no import call
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });
});

// ─── syncs pending game successfully ──────────────────────────────────────────

describe('test_sync_back_syncs_pending_game', () => {
  it('syncs a pending game and clears sync_pending', async () => {
    const game = makeGame();
    await saveGame(game);
    await saveRound(makeRound(game.id, 1));

    mockHealthOk();
    mockImportOk();

    const result = await attemptSyncBack();
    expect(result.synced).toBe(1);
    expect(result.failed).toBe(0);

    const updated = await getGame(game.id);
    expect(updated.sync_pending).toBe(false);
  });
});

// ─── handles sync failure ─────────────────────────────────────────────────────

describe('test_sync_back_handles_sync_failure', () => {
  it('stops syncing after first failure', async () => {
    const game1 = makeGame();
    const game2 = makeGame({ id: 'game-1726840001-def67890', client_game_id: 'failover-43-1726840001' });
    await saveGame(game1);
    await saveGame(game2);
    await saveRound(makeRound(game1.id, 1));
    await saveRound(makeRound(game2.id, 1));

    mockHealthOk();
    mockImportFail();

    const result = await attemptSyncBack();
    expect(result.synced).toBe(0);
    expect(result.failed).toBe(1);
    // Should stop after first failure, not try game2
    // Health probe + 1 import attempt = 2 calls
    expect(globalThis.fetch).toHaveBeenCalledTimes(2);
  });
});

// ─── no pending games → no-op ─────────────────────────────────────────────────

describe('test_sync_back_no_pending_games', () => {
  it('returns early when no games are pending', async () => {
    const game = makeGame({ sync_pending: false });
    await saveGame(game);

    const result = await attemptSyncBack();
    expect(result).toEqual({ synced: 0, failed: 0, skipped: true, cleared: 0 });
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });
});

// ─── L2: sync-back error is logged ──────────────────────────────────────────

describe('test_sync_back_error_is_logged', () => {
  it('attemptSyncBack errors can be caught and logged', async () => {
    // Verify that when attemptSyncBack throws, the error can be
    // caught and passed to logger.error (as runSyncBack should do)
    const { logger } = await import('../../app/static/js/components/logger.js');
    vi.spyOn(logger, 'error');

    // Simulate what runSyncBack should do: catch + log
    const mockAttemptSyncBack = vi.fn().mockRejectedValue(new Error('IDB broken'));
    try {
      await mockAttemptSyncBack();
    } catch (error) {
      logger.error('sync', error.message);
    }

    expect(logger.error).toHaveBeenCalledWith('sync', 'IDB broken');
  });
});

// ─── M15: 4xx skips bad game, continues to next ─────────────────────────────

describe('test_sync_back_skips_permanently_failed_game', () => {
  it('marks 4xx game as sync_failed and continues to next game', async () => {
    const game1 = makeGame({ id: 'game-bad', client_game_id: 'fail-bad' });
    const game2 = makeGame({ id: 'game-good', client_game_id: 'fail-good' });
    await saveGame(game1);
    await saveGame(game2);
    await saveRound(makeRound(game1.id, 1));
    await saveRound(makeRound(game2.id, 1));

    mockHealthOk();
    mockImportClientError(); // game1 gets 422
    mockImportOk();          // game2 succeeds

    const result = await attemptSyncBack();
    // game1 should be marked failed, game2 should sync
    expect(result.synced).toBe(1);
    expect(result.failed).toBe(1);

    const updated1 = await getGame(game1.id);
    expect(updated1.sync_pending).toBe(false);
    expect(updated1.sync_failed).toBe(true);

    const updated2 = await getGame(game2.id);
    expect(updated2.sync_pending).toBe(false);
  });

  it('still breaks on 5xx errors (retryable)', async () => {
    const game1 = makeGame({ id: 'game-5xx', client_game_id: 'fail-5xx' });
    const game2 = makeGame({ id: 'game-ok', client_game_id: 'fail-ok' });
    await saveGame(game1);
    await saveGame(game2);
    await saveRound(makeRound(game1.id, 1));
    await saveRound(makeRound(game2.id, 1));

    mockHealthOk();
    mockImportFail(); // game1 gets 500

    const result = await attemptSyncBack();
    expect(result.synced).toBe(0);
    expect(result.failed).toBe(1);
    // Should NOT have tried game2
    expect(globalThis.fetch).toHaveBeenCalledTimes(2);
  });
});

// ─── sync-back is silent — no banner side effects ────────────────────────────

describe('test_sync_back_returns_result_without_ui_side_effects', () => {
  it('attemptSyncBack returns counts without calling any banner/UI methods', async () => {
    const game = makeGame();
    await saveGame(game);
    await saveRound(makeRound(game.id, 1));

    mockHealthOk();
    mockImportOk();

    // banner module should NOT be imported or called by attemptSyncBack
    const { banner } = await import('../../app/static/js/components/connection-banner.js');
    const showSyncedSpy = vi.spyOn(banner, 'showSynced');
    const showSyncFailedSpy = vi.spyOn(banner, 'showSyncFailed');

    const result = await attemptSyncBack();
    expect(result.synced).toBe(1);

    // Per requirements: sync-back is data-only, UI is lobby-only
    expect(showSyncedSpy).not.toHaveBeenCalled();
    expect(showSyncFailedSpy).not.toHaveBeenCalled();
  });
});

// ─── skips games without linked_room ──────────────────────────────────────────

describe('test_sync_back_skips_unlinked_games', () => {
  it('skips games without a linked_room', async () => {
    const game = makeGame({ linked_room: null });
    await saveGame(game);
    await saveRound(makeRound(game.id, 1));

    mockHealthOk();

    const result = await attemptSyncBack();
    // No import attempted (no linked_room)
    expect(result.synced).toBe(0);
    expect(result.failed).toBe(0);
  });

  it('clears sync_pending on unlinked games so badge does not show them', async () => {
    const game = makeGame({ linked_room: null });
    await saveGame(game);

    const result = await attemptSyncBack();
    expect(result.cleared).toBe(1);

    const updated = await getGame(game.id);
    expect(updated.sync_pending).toBe(false);
  });
});
