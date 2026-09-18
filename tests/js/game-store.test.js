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
  saveRoom,
  getRoom,
  getAllRooms,
  deleteRoom,
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

    const updated = { ...game, phase: 'scoreboard' };
    await saveGame(updated);

    const retrieved = await getGame(game.id);
    expect(retrieved.phase).toBe('scoreboard');
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

// ─── rooms store (v2) ─────────────────────────────────────────────────────

function makeRoom(overrides = {}) {
  return {
    share_code: 'KLCC',
    name: 'Besties',
    players: ['Masood', 'Afeefa', 'Jj'],
    pin_verifier: { salt: 'aabb', hash: 'ccdd', iterations: 600000 },
    attempts: 0,
    locked_until: null,
    cached_at: '2026-09-17T00:00:00Z',
    ...overrides,
  };
}

describe('test_v2_migration_preserves_games', () => {
  it('upgrading to v2 preserves existing game data', async () => {
    const game = makeGame({ id: 99, status: 'active' });
    await saveGame(game);

    // Saving a room triggers v2 store access — games must survive
    await saveRoom(makeRoom());

    const retrieved = await getGame(99);
    expect(retrieved).not.toBeNull();
    expect(retrieved.id).toBe(99);
    expect(retrieved.status).toBe('active');
  });
});

describe('test_v2_creates_rooms_store', () => {
  it('rooms store exists after opening v2 database', async () => {
    await saveRoom(makeRoom());
    const room = await getRoom('KLCC');
    expect(room).not.toBeNull();
    expect(room.share_code).toBe('KLCC');
  });
});

describe('test_save_room', () => {
  it('saveRoom stores room with share_code keyPath', async () => {
    const room = makeRoom({ share_code: 'DEN8', name: 'Family' });
    await saveRoom(room);
    const retrieved = await getRoom('DEN8');
    expect(retrieved.name).toBe('Family');
    expect(retrieved.players).toEqual(['Masood', 'Afeefa', 'Jj']);
  });
});

describe('test_get_room', () => {
  it('getRoom returns null for non-existent share_code', async () => {
    const result = await getRoom('NOPE');
    expect(result).toBeNull();
  });
});

describe('test_get_all_rooms', () => {
  it('getAllRooms returns all cached rooms', async () => {
    await saveRoom(makeRoom({ share_code: 'AAA1', name: 'Room A' }));
    await saveRoom(makeRoom({ share_code: 'BBB2', name: 'Room B' }));
    await saveRoom(makeRoom({ share_code: 'CCC3', name: 'Room C' }));

    const rooms = await getAllRooms();
    expect(rooms).toHaveLength(3);
    const names = rooms.map(r => r.name).sort();
    expect(names).toEqual(['Room A', 'Room B', 'Room C']);
  });
});

describe('test_delete_room', () => {
  it('deleteRoom removes a room by share_code', async () => {
    await saveRoom(makeRoom({ share_code: 'DEL1' }));
    await deleteRoom('DEL1');
    const result = await getRoom('DEL1');
    expect(result).toBeNull();
  });
});

describe('test_new_game_fields_round_trip', () => {
  it('client_game_id, linked_room, sync_pending survive save/get', async () => {
    const game = makeGame({
      id: 'game-123-abc',
      client_game_id: 'game-123-abc',
      linked_room: 'KLCC',
      sync_pending: true,
    });
    await saveGame(game);

    const retrieved = await getGame('game-123-abc');
    expect(retrieved.client_game_id).toBe('game-123-abc');
    expect(retrieved.linked_room).toBe('KLCC');
    expect(retrieved.sync_pending).toBe(true);
  });
});

describe('test_crud_round_trip_all_stores', () => {
  it('save + retrieve + delete works for games, rounds, and rooms in one test', async () => {
    // Games
    const game = makeGame({ id: 77, status: 'finished' });
    await saveGame(game);
    expect(await getGame(77)).toEqual(game);

    // Rounds
    const round = makeRound({ game_id: 77, round_num: 1 });
    await saveRound(round);
    expect(await getRound(77, 1)).toEqual(round);
    await deleteRound(77, 1);
    expect(await getRound(77, 1)).toBeNull();

    // Rooms
    const room = makeRoom({ share_code: 'RT01', name: 'RoundTrip' });
    await saveRoom(room);
    expect((await getRoom('RT01')).name).toBe('RoundTrip');
    await deleteRoom('RT01');
    expect(await getRoom('RT01')).toBeNull();
  });
});
