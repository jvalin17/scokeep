/**
 * Scoresheet round lock — apply buffered scores to IDB round (no network).
 */
import 'fake-indexeddb/auto';
import { IDBFactory } from 'fake-indexeddb';
import { describe, it, expect, beforeEach } from 'vitest';
import {
  resetForTesting,
  setIndexedDBForTesting,
  getRound,
} from '../../app/static/js/engine/store.js';
import {
  createGame,
  lockScoresheetRound,
  getScoreboard,
  getGame,
} from '../../app/static/js/engine/game-engine.js';

beforeEach(() => {
  resetForTesting();
  setIndexedDBForTesting(new IDBFactory());
});

describe('lockScoresheetRound', () => {
  it('writes scores, marks complete, moves to scoreboard', async () => {
    const game = await createGame(['Maria', 'Diego'], {
      game_type: 'scoresheet',
      show_totals: true,
      winner: 'highest',
    });
    const round = await lockScoresheetRound(game.id, { 0: 15, 1: 7 });
    expect(round.status).toBe('complete');
    expect(round.scores).toEqual({ 0: 15, 1: 7 });
    const updated = await getGame(game.id);
    expect(updated.phase).toBe('scoreboard');
    const board = await getScoreboard(game.id);
    expect(board.totals['0']).toBe(15);
    expect(board.totals['1']).toBe(7);
  });

  it('uses intermission when show_totals is off', async () => {
    const game = await createGame(['Maria', 'Diego'], {
      game_type: 'scoresheet',
      show_totals: false,
    });
    await lockScoresheetRound(game.id, { 0: 1, 1: 2 });
    const updated = await getGame(game.id);
    expect(updated.phase).toBe('intermission');
    const stored = await getRound(game.id, 1);
    expect(stored.status).toBe('complete');
  });
});
