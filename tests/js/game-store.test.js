import 'fake-indexeddb/auto';
import { IDBFactory } from 'fake-indexeddb';
import { describe, it, expect, beforeEach } from 'vitest';
import {
  openGameStore,
  saveGame,
  getGame,
  getActiveGame,
  saveRound,
  getRound,
  getRoundsForGame,
  deleteRound,
  getFinishedGames,
  resetForTesting,
  setIndexedDBForTesting,
} from '../../app/static/js/engine/store.js';

// Give each test a fully isolated, empty IndexedDB by replacing the global
// factory with a brand-new IDBFactory instance before every test.
beforeEach(() => {
  resetForTesting();
  setIndexedDBForTesting(new IDBFactory());
});

// ─── helpers ────────────────────────────────────────────────────────────────

function makeGame(overrides = {}) {
  return {
    id: 1,
    playground_id: 10,
    players: ['Alice', 'Bob'],
    settings: { variant: 'standard' },
    current_round: 1,
    total_rounds: 5,
    phase: 'bidding',
    dealer_index: 0,
    status: 'active',
    mode: 'online',
    synced_at: null,
    started_at: '2026-09-08T10:00:00Z',
    finished_at: null,
    ...overrides,
  };
}

function makeRound(overrides = {}) {
  return {
    game_id: 1,
    round_num: 1,
    cards_dealt: 5,
    trump_suit: 'spades',
    bids: [2, 1],
    hands_won: [2, 1],
    scores: [10, 10],
    status: 'complete',
    ...overrides,
  };
}

// ─── tests ───────────────────────────────────────────────────────────────────

describe('test_open_creates_database', () => {
  it('openGameStore() resolves without error', async () => {
    await expect(openGameStore()).resolves.not.toThrow();
  });
});

describe('test_save_game_and_retrieve', () => {
  it('saveGame then getGame returns identical object', async () => {
    const game = makeGame();
    await saveGame(game);
    const retrieved = await getGame(game.id);
    expect(retrieved).toEqual(game);
  });
});

describe('test_update_game_overwrites', () => {
  it('second saveGame with same id overwrites the first', async () => {
    const game = makeGame({ phase: 'bidding' });
    await saveGame(game);

    const updated = { ...game, phase: 'scoring' };
    await saveGame(updated);

    const retrieved = await getGame(game.id);
    expect(retrieved.phase).toBe('scoring');
  });
});

describe('test_get_nonexistent_returns_null', () => {
  it('getGame with unknown id returns null', async () => {
    const result = await getGame(999);
    expect(result).toBeNull();
  });
});

describe('test_save_round_and_retrieve', () => {
  it('saveRound then getRound returns the round', async () => {
    const round = makeRound();
    await saveRound(round);
    const retrieved = await getRound(round.game_id, round.round_num);
    expect(retrieved).toEqual(round);
  });
});

describe('test_get_rounds_for_game', () => {
  it('getRoundsForGame returns all rounds sorted by round_num', async () => {
    // Save in non-sequential order to verify sorting.
    await saveRound(makeRound({ round_num: 3 }));
    await saveRound(makeRound({ round_num: 1 }));
    await saveRound(makeRound({ round_num: 2 }));

    const rounds = await getRoundsForGame(1);
    expect(rounds).toHaveLength(3);
    expect(rounds.map((r) => r.round_num)).toEqual([1, 2, 3]);
  });
});

describe('test_delete_round', () => {
  it('deleteRound removes the round so getRound returns null', async () => {
    const round = makeRound();
    await saveRound(round);
    await deleteRound(round.game_id, round.round_num);
    const result = await getRound(round.game_id, round.round_num);
    expect(result).toBeNull();
  });
});

describe('test_get_active_game', () => {
  it('getActiveGame returns the game with status=active', async () => {
    const active = makeGame({ id: 1, status: 'active' });
    const finished = makeGame({ id: 2, status: 'finished' });
    await saveGame(finished);
    await saveGame(active);

    const result = await getActiveGame();
    expect(result).not.toBeNull();
    expect(result.status).toBe('active');
    expect(result.id).toBe(1);
  });
});

describe('test_get_active_game_returns_null_when_none', () => {
  it('getActiveGame returns null when no active game exists', async () => {
    await saveGame(makeGame({ id: 5, status: 'finished' }));
    const result = await getActiveGame();
    expect(result).toBeNull();
  });
});

describe('test_get_finished_games', () => {
  it('getFinishedGames returns only finished games up to limit', async () => {
    await saveGame(makeGame({ id: 1, status: 'finished' }));
    await saveGame(makeGame({ id: 2, status: 'finished' }));
    await saveGame(makeGame({ id: 3, status: 'finished' }));
    await saveGame(makeGame({ id: 4, status: 'active' }));

    const results = await getFinishedGames(2);
    expect(results.length).toBe(2);
    expect(results.every((g) => g.status === 'finished')).toBe(true);
  });
});
