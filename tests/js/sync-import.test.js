import 'fake-indexeddb/auto';
import { IDBFactory } from 'fake-indexeddb';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  saveGame,
  saveRound,
  getGame,
  resetForTesting,
  setIndexedDBForTesting,
} from '../../app/static/js/engine/store.js';

import { syncOneGame, getSyncPendingGames } from '../../app/static/js/engine/sync-import.js';

// ─── helpers ────────────────────────────────────────────────────────────────

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

function makeRound(gameId, roundNum) {
  return {
    game_id: gameId,
    round_num: roundNum,
    cards_dealt: 8,
    trump_suit: 'spades',
    bids: { '0': 2, '1': 1, '2': 0 },
    hands_won: { '0': 2, '1': 1, '2': 0 },
    scores: { '0': 20, '1': 11, '2': 10 },
    status: 'complete',
  };
}

// ─── setup ──────────────────────────────────────────────────────────────────

beforeEach(() => {
  resetForTesting();
  setIndexedDBForTesting(new IDBFactory());
  vi.restoreAllMocks();
});

// ─── syncOneGame ────────────────────────────────────────────────────────────

describe('test_sync_one_game_posts_correct_payload', () => {
  it('syncOneGame POSTs game data to import endpoint', async () => {
    const game = makeLinkedGame();
    await saveGame(game);
    await saveRound(makeRound(game.id, 1));

    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ game_id: 42, rounds_imported: 1 }),
    });
    vi.stubGlobal('fetch', fetchSpy);

    const result = await syncOneGame(game);
    expect(fetchSpy).toHaveBeenCalledOnce();

    const [url, options] = fetchSpy.mock.calls[0];
    expect(url).toBe('/api/game/KLCC/import');
    expect(options.method).toBe('POST');

    const body = JSON.parse(options.body);
    expect(body.client_game_id).toBe(game.client_game_id);
    expect(body.players).toEqual(['Anjum', 'Masood', 'Lala']);
    expect(body.rounds).toHaveLength(1);
    expect(body.rounds[0].round_num).toBe(1);
    expect(result.success).toBe(true);
  });
});

describe('test_sync_one_game_marks_not_pending_on_success', () => {
  it('syncOneGame sets sync_pending=false in IDB on 200', async () => {
    const game = makeLinkedGame();
    await saveGame(game);
    await saveRound(makeRound(game.id, 1));

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ game_id: 42, rounds_imported: 1 }),
    }));

    await syncOneGame(game);

    const updated = await getGame(game.id);
    expect(updated.sync_pending).toBe(false);
  });
});

describe('test_sync_one_game_keeps_pending_on_failure', () => {
  it('syncOneGame keeps sync_pending=true on fetch failure', async () => {
    const game = makeLinkedGame();
    await saveGame(game);
    await saveRound(makeRound(game.id, 1));

    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network error')));

    const result = await syncOneGame(game);
    expect(result.success).toBe(false);

    const updated = await getGame(game.id);
    expect(updated.sync_pending).toBe(true);
  });
});

describe('test_sync_one_game_keeps_pending_on_non_ok', () => {
  it('syncOneGame keeps sync_pending=true on non-200 response', async () => {
    const game = makeLinkedGame();
    await saveGame(game);
    await saveRound(makeRound(game.id, 1));

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: 'Not authenticated' }),
    }));

    const result = await syncOneGame(game);
    expect(result.success).toBe(false);
    expect(result.error).toContain('401');

    const updated = await getGame(game.id);
    expect(updated.sync_pending).toBe(true);
  });
});

describe('test_sync_one_game_returns_status_on_4xx', () => {
  it('syncOneGame returns numeric status on 4xx so callers can distinguish permanent failures', async () => {
    const game = makeLinkedGame();
    await saveGame(game);
    await saveRound(makeRound(game.id, 1));

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: () => Promise.resolve({ detail: 'Duplicate game' }),
    }));

    const result = await syncOneGame(game);
    expect(result.success).toBe(false);
    expect(result.status).toBe(409);

    // sync_pending stays true — it's the caller's job to clear it for 4xx
    const updated = await getGame(game.id);
    expect(updated.sync_pending).toBe(true);
  });
});

// ─── getSyncPendingGames ────────────────────────────────────────────────────

describe('test_get_sync_pending_games_filters_by_room', () => {
  it('getSyncPendingGames returns only pending games for a specific room', async () => {
    await saveGame(makeLinkedGame({ id: 'g1', client_game_id: 'g1', linked_room: 'KLCC', sync_pending: true }));
    await saveGame(makeLinkedGame({ id: 'g2', client_game_id: 'g2', linked_room: 'KLCC', sync_pending: false }));
    await saveGame(makeLinkedGame({ id: 'g3', client_game_id: 'g3', linked_room: 'OTHER', sync_pending: true }));
    await saveGame(makeLinkedGame({ id: 'g4', client_game_id: 'g4', linked_room: 'KLCC', sync_pending: true }));

    const pending = await getSyncPendingGames('KLCC');
    expect(pending).toHaveLength(2);
    expect(pending.map(g => g.id).sort()).toEqual(['g1', 'g4']);
  });
});

describe('test_get_sync_pending_games_returns_empty_when_none', () => {
  it('getSyncPendingGames returns empty array when no pending games', async () => {
    await saveGame(makeLinkedGame({ sync_pending: false }));

    const pending = await getSyncPendingGames('KLCC');
    expect(pending).toHaveLength(0);
  });
});
