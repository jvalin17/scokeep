/**
 * game-store.test.js — L12: Test IDB game purge functionality.
 *
 * Run with: npx vitest run tests/js/game-store.test.js
 */

import 'fake-indexeddb/auto';
import { IDBFactory } from 'fake-indexeddb';
import { describe, it, expect, beforeEach } from 'vitest';
import {
  resetForTesting,
  setIndexedDBForTesting,
  saveGame,
  getGame,
  purgeOldGames,
} from '../../app/static/js/engine/store.js';

beforeEach(() => {
  resetForTesting();
  setIndexedDBForTesting(new IDBFactory());
});

function makeGame(index) {
  return {
    id: `game-${index}`,
    players: ['A', 'B'],
    settings: {},
    current_round: 1,
    total_rounds: 7,
    dealer_index: 0,
    phase: 'final',
    status: 'finished',
    started_at: new Date(2026, 0, 1, 0, 0, index).toISOString(),
    finished_at: new Date(2026, 0, 1, 1, 0, index).toISOString(),
  };
}

describe('test_purge_old_games', () => {
  it('keeps only maxCount most recent games', async () => {
    for (let i = 0; i < 30; i++) {
      await saveGame(makeGame(i));
    }

    const purged = await purgeOldGames(20);
    expect(purged).toBe(10);

    const newest = await getGame('game-29');
    expect(newest).toBeTruthy();

    const oldest = await getGame('game-0');
    expect(oldest).toBeFalsy();
  });

  it('does nothing when under maxCount', async () => {
    for (let i = 0; i < 5; i++) {
      await saveGame(makeGame(i));
    }

    const purged = await purgeOldGames(20);
    expect(purged).toBe(0);
  });
});
