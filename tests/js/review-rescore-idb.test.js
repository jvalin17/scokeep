/**
 * IDB review rescore — edit hands after game ends, before confirmFinal.
 * Run: npx vitest run tests/js/review-rescore-idb.test.js
 */

import 'fake-indexeddb/auto';
import { IDBFactory } from 'fake-indexeddb';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  resetForTesting,
  setIndexedDBForTesting,
  getGame,
} from '../../app/static/js/engine/store.js';

vi.mock('../../app/static/js/engine/sync-manager.js', () => ({
  syncManager: {
    syncRound: vi.fn(() => Promise.resolve({ success: true })),
    syncGame: vi.fn(() => Promise.resolve({ success: true })),
    retrySyncQueue: vi.fn(() => Promise.resolve({ drained: true, remaining: 0, failed: false })),
  },
  isLocalId: (gameId) => typeof gameId === 'string' && gameId.startsWith('game-'),
}));

import {
  createGame,
  submitBid,
  submitHands,
  endRound,
  endGame,
  rescoreRound,
  getScoreboard,
  confirmFinal,
} from '../../app/static/js/game-api.js';

beforeEach(() => {
  resetForTesting();
  setIndexedDBForTesting(new IDBFactory());
});

async function playOneRound(gameId, cardsDealt) {
  await submitBid(gameId, 0, 0);
  await submitBid(gameId, 1, 0);
  await submitHands(gameId, 0, 0);
  await submitHands(gameId, 1, cardsDealt);
  await endRound(gameId);
}

describe('IDB review rescore after game', () => {
  it('updates scores when a finished-game round is edited', async () => {
    const game = await createGame(['Alice', 'Bob'], {
      formula: 'kachuful_standard',
      must_lose: false,
      rounds_per_set: 1,
      num_sets: 1,
    });
    const { cards_dealt: cardsDealt } = await (
      await import('../../app/static/js/engine/store.js')
    ).getRound(game.id, 1);

    await playOneRound(game.id, cardsDealt);
    await endGame(game.id);

    const before = await getScoreboard(game.id);
    const beforeAlice = before.totals['0'];

    await rescoreRound(game.id, 1);
    // Clear then re-assign (same constraint as live keypad: remaining cards)
    await submitHands(game.id, 0, 0);
    await submitHands(game.id, 1, 0);
    await submitHands(game.id, 0, cardsDealt);
    await submitHands(game.id, 1, 0);
    await endRound(game.id);

    const after = await getScoreboard(game.id);
    expect(after.totals['0']).not.toBe(beforeAlice);
    expect(after.rounds[0].hands_won['0']).toBe(cardsDealt);
    expect(after.rounds[0].hands_won['1']).toBe(0);

    await confirmFinal(game.id);
    const finalGame = await getGame(game.id);
    expect(finalGame.phase).toBe('final');
    expect(finalGame.status).toBe('finished');
  });

  it('returns to review phase after rescoring from review (not scoreboard)', async () => {
    const game = await createGame(['Alice', 'Bob'], {
      formula: 'kachuful_standard',
      must_lose: false,
      rounds_per_set: 1,
      num_sets: 1,
    });
    const roundMod = await import('../../app/static/js/engine/store.js');
    const { cards_dealt: cardsDealt } = await roundMod.getRound(game.id, 1);
    await playOneRound(game.id, cardsDealt);
    await endGame(game.id);
    expect((await getGame(game.id)).phase).toBe('review');

    await rescoreRound(game.id, 1);
    await submitHands(game.id, 0, 0);
    await submitHands(game.id, 1, 0);
    await submitHands(game.id, 0, cardsDealt);
    await submitHands(game.id, 1, 0);
    await endRound(game.id);

    const after = await getGame(game.id);
    expect(after.phase).toBe('review');
  });
});
