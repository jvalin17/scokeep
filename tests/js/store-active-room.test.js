/**
 * getActiveGameForRoom — find the active IDB game linked to a room.
 * Used by lobby resume after IDB-first start (local game- ids).
 */
import 'fake-indexeddb/auto';
import { IDBFactory } from 'fake-indexeddb';
import { describe, it, expect, beforeEach } from 'vitest';
import {
  resetForTesting,
  setIndexedDBForTesting,
  saveGame,
  getActiveGameForRoom,
} from '../../app/static/js/engine/store.js';

beforeEach(() => {
  resetForTesting();
  setIndexedDBForTesting(new IDBFactory());
});

describe('test_get_active_game_for_room', () => {
  it('returns the active game for the matching linked_room', async () => {
    await saveGame({
      id: 'game-room-a',
      status: 'active',
      linked_room: 'KLCC',
      players: ['Anjum', 'Masood'],
      phase: 'bidding',
      current_round: 1,
      settings: {},
    });
    await saveGame({
      id: 'game-room-b',
      status: 'active',
      linked_room: 'ABCD',
      players: ['Lala', 'Bob'],
      phase: 'playing',
      current_round: 2,
      settings: {},
    });

    const found = await getActiveGameForRoom('KLCC');
    expect(found.id).toBe('game-room-a');
    expect(found.linked_room).toBe('KLCC');
  });

  it('returns null when no active game matches the room', async () => {
    await saveGame({
      id: 'game-other',
      status: 'active',
      linked_room: 'ZZZZ',
      players: ['Alice'],
      phase: 'bidding',
      current_round: 1,
      settings: {},
    });
    expect(await getActiveGameForRoom('KLCC')).toBeNull();
  });
});
