/**
 * game-engine.test.js — Integration tests for the game orchestrator.
 *
 * Each test gets a fully isolated IndexedDB via fake-indexeddb.
 * Run with: npx vitest run tests/js/game-engine.test.js
 */

import 'fake-indexeddb/auto';
import { IDBFactory } from 'fake-indexeddb';
import { describe, it, expect, beforeEach } from 'vitest';
import {
  resetForTesting,
  setIndexedDBForTesting,
} from '../../app/static/js/engine/store.js';
import {
  createGame,
  getGame,
  submitBid,
  getBids,
  editBid,
  startRound,
  enterRoundEnd,
  submitHands,
  endRound,
  nextRound,
  endGame,
  extendGame,
  getScoreboard,
  undoRound,
  confirmFinal,
} from '../../app/static/js/engine/game-engine.js';

// ─── isolation ───────────────────────────────────────────────────────────────

beforeEach(() => {
  resetForTesting();
  setIndexedDBForTesting(new IDBFactory());
});

// ─── helpers ─────────────────────────────────────────────────────────────────

/** Two players, standard settings, 16 rounds (2 sets). */
function makePlayers() {
  return ['Alice', 'Bob'];
}

function makeSettings(overrides = {}) {
  return {
    formula: 'kachuful_standard',
    must_lose: true,
    rounds_per_set: 8,
    num_sets: 2,
    ...overrides,
  };
}

/**
 * Play one complete round for a 2-player game.
 * Bids and hands are provided explicitly for control.
 */
async function playRound(gameId, bids, handsWon) {
  for (let i = 0; i < bids.length; i++) {
    await submitBid(gameId, i, bids[i]);
  }
  await startRound(gameId);
  await enterRoundEnd(gameId);
  for (let i = 0; i < handsWon.length; i++) {
    await submitHands(gameId, i, handsWon[i]);
  }
  await endRound(gameId);
}

// ─── tests ───────────────────────────────────────────────────────────────────

describe('test_create_game_initializes_state', () => {
  it('createGame returns game with round=1, phase=bidding, correct total_rounds', async () => {
    const players = makePlayers();
    const settings = makeSettings();
    const game = await createGame(players, settings);

    expect(game.current_round).toBe(1);
    expect(game.phase).toBe('bidding');
    // 2 sets × 8 rounds/set = 16 total rounds
    expect(game.total_rounds).toBe(16);
    expect(game.players).toEqual(players);
    expect(game.status).toBe('active');
    expect(game.dealer_index).toBe(0);
    expect(typeof game.id).toBe('string');
    expect(game.started_at).not.toBeNull();
  });
});

describe('test_create_game_persists_to_store', () => {
  it('after createGame, getGame(id) returns the game', async () => {
    const game = await createGame(makePlayers(), makeSettings());
    const retrieved = await getGame(game.id);

    expect(retrieved).not.toBeNull();
    expect(retrieved.id).toBe(game.id);
    expect(retrieved.phase).toBe('bidding');
    expect(retrieved.current_round).toBe(1);
  });
});

describe('test_submit_bid_stores_bid', () => {
  it('submitBid(gameId, 0, 2) adds bid to round.bids', async () => {
    const game = await createGame(makePlayers(), makeSettings());
    await submitBid(game.id, 0, 2);

    const bids = await getBids(game.id);
    expect(bids['0']).toBe(2);
  });
});

describe('test_submit_bid_rejects_must_lose', () => {
  it('must-lose constraint triggers error for last bidder', async () => {
    const game = await createGame(makePlayers(), makeSettings({ must_lose: true }));
    // Round 1: 8 cards dealt. Alice bids 3. Bob's bid of 5 would total 8 = cards.
    await submitBid(game.id, 0, 3);

    await expect(submitBid(game.id, 1, 5)).rejects.toThrow(/must-lose/i);
  });
});

describe('test_start_round_sets_playing', () => {
  it('startRound sets phase to playing after all bids placed', async () => {
    const game = await createGame(makePlayers(), makeSettings());
    await submitBid(game.id, 0, 1);
    await submitBid(game.id, 1, 0);
    await startRound(game.id);

    const updated = await getGame(game.id);
    expect(updated.phase).toBe('playing');
  });
});

describe('test_enter_round_end_sets_phase', () => {
  it('enterRoundEnd sets phase to round_end', async () => {
    const game = await createGame(makePlayers(), makeSettings());
    await submitBid(game.id, 0, 1);
    await submitBid(game.id, 1, 0);
    await startRound(game.id);
    await enterRoundEnd(game.id);

    const updated = await getGame(game.id);
    expect(updated.phase).toBe('round_end');
  });
});

describe('test_submit_hands_stores_hands', () => {
  it('submitHands(gameId, 0, 2) adds to round.hands_won', async () => {
    const game = await createGame(makePlayers(), makeSettings());
    await submitBid(game.id, 0, 1);
    await submitBid(game.id, 1, 0);
    await startRound(game.id);
    await enterRoundEnd(game.id);
    await submitHands(game.id, 0, 2);

    // Read round from store to inspect hands_won
    const { getRound } = await import('../../app/static/js/engine/store.js');
    const round = await getRound(game.id, 1);
    expect(round.hands_won['0']).toBe(2);
  });
});

describe('test_submit_hands_rejects_exceeding', () => {
  it('hands > remaining cards are rejected', async () => {
    const game = await createGame(makePlayers(), makeSettings());
    await submitBid(game.id, 0, 1);
    await submitBid(game.id, 1, 0);
    await startRound(game.id);
    await enterRoundEnd(game.id);
    // Round 1 has 8 cards dealt. Submitting 9 should fail.
    await expect(submitHands(game.id, 0, 9)).rejects.toThrow(/exceeds/i);
  });
});

describe('test_end_round_calculates_scores', () => {
  it('endRound computes scores using the scoring engine', async () => {
    const game = await createGame(makePlayers(), makeSettings());
    // Round 1: 8 cards dealt. Alice bids 3 and wins 3 (hit). Bob bids 4 and wins 5 (miss).
    await submitBid(game.id, 0, 3);
    await submitBid(game.id, 1, 4);
    await startRound(game.id);
    await enterRoundEnd(game.id);
    await submitHands(game.id, 0, 3);
    await submitHands(game.id, 1, 5);
    await endRound(game.id);

    const { getRound } = await import('../../app/static/js/engine/store.js');
    const round = await getRound(game.id, 1);
    // Alice bid 3, won 3 → 3*10 = 30. Bob bid 4, won 5 → -(4*10) = -40.
    expect(round.scores['0']).toBe(30);
    expect(round.scores['1']).toBe(-40);
  });
});

describe('test_next_round_advances', () => {
  it('nextRound increments round and rotates dealer', async () => {
    const game = await createGame(makePlayers(), makeSettings());
    await submitBid(game.id, 0, 1);
    await submitBid(game.id, 1, 0);
    await startRound(game.id);
    await enterRoundEnd(game.id);
    await submitHands(game.id, 0, 1);
    await submitHands(game.id, 1, 7);
    await endRound(game.id);
    await nextRound(game.id);

    const updated = await getGame(game.id);
    expect(updated.current_round).toBe(2);
    expect(updated.dealer_index).toBe(1);
    expect(updated.phase).toBe('bidding');
  });
});

describe('test_next_round_last_enters_review', () => {
  it('on final round, nextRound sets phase to review', async () => {
    // Use a 1-round game for simplicity.
    const settings = makeSettings({ num_sets: 1, rounds_per_set: 1 });
    const game = await createGame(makePlayers(), settings);
    expect(game.total_rounds).toBe(1);

    await submitBid(game.id, 0, 0);
    await submitBid(game.id, 1, 0);
    await startRound(game.id);
    await enterRoundEnd(game.id);
    await submitHands(game.id, 0, 0);
    await submitHands(game.id, 1, 1);
    await endRound(game.id);
    await nextRound(game.id);

    const updated = await getGame(game.id);
    expect(updated.phase).toBe('review');
  });
});

describe('test_get_scoreboard_returns_totals', () => {
  it('getScoreboard returns cumulative totals after one scored round', async () => {
    const game = await createGame(makePlayers(), makeSettings());
    await submitBid(game.id, 0, 2);
    await submitBid(game.id, 1, 3);
    await startRound(game.id);
    await enterRoundEnd(game.id);
    await submitHands(game.id, 0, 2);
    await submitHands(game.id, 1, 6);
    await endRound(game.id);

    const scoreboard = await getScoreboard(game.id);
    // Alice bid 2, won 2 → 2*10 = 20. Bob bid 3, won 6 → -(3*10) = -30.
    expect(scoreboard.totals['0']).toBe(20);
    expect(scoreboard.totals['1']).toBe(-30);
    expect(scoreboard.rounds).toHaveLength(1);
  });
});

describe('test_full_2_round_game', () => {
  it('play 2 complete rounds, verify final totals match scoring vectors', async () => {
    const game = await createGame(makePlayers(), makeSettings());

    // Round 1: 8 cards
    //   Alice bids 2, wins 2 → +20
    //   Bob bids 3, wins 6   → -30
    await playRound(game.id, [2, 3], [2, 6]);
    await nextRound(game.id);

    // Round 2: 7 cards
    //   Alice bids 1, wins 1 → +11 (kachuful_standard bid=1 hit)
    //   Bob bids 2, wins 1   → -20 (miss)
    await playRound(game.id, [1, 2], [1, 6]);
    await nextRound(game.id);

    const scoreboard = await getScoreboard(game.id);
    expect(scoreboard.rounds).toHaveLength(2);
    // Alice: 20 + 11 = 31
    expect(scoreboard.totals['0']).toBe(31);
    // Bob: -30 + (-20) = -50
    expect(scoreboard.totals['1']).toBe(-50);
  });
});

describe('test_end_game_sets_review_phase', () => {
  it('endGame sets phase=review (not finished), status=finished', async () => {
    const game = await createGame(makePlayers(), makeSettings());
    const result = await endGame(game.id);

    expect(result.phase).toBe('review');
    expect(result.status).toBe('finished');
    expect(result.finished_at).not.toBeNull();
  });
});

describe('test_confirm_final_sets_final_phase', () => {
  it('confirmFinal sets phase=final, status=finished independently of endGame', async () => {
    const game = await createGame(makePlayers(), makeSettings());
    const result = await confirmFinal(game.id);

    expect(result.phase).toBe('final');
    expect(result.status).toBe('finished');
  });
});

describe('test_undo_round_at_round_1_sets_bidding', () => {
  it('undoRound from round 1 sets phase=bidding', async () => {
    const game = await createGame(makePlayers(), makeSettings());
    await playRound(game.id, [1, 0], [1, 7]);
    // Still on round 1 after endRound (scoring phase), undo it
    const result = await undoRound(game.id);

    expect(result.current_round).toBe(1);
    expect(result.phase).toBe('bidding');
  });
});

describe('test_undo_round_after_round_2_sets_scoreboard', () => {
  it('undoRound from round 2 sets phase=scoreboard', async () => {
    const game = await createGame(makePlayers(), makeSettings());
    await playRound(game.id, [1, 0], [1, 7]);
    await nextRound(game.id);
    await playRound(game.id, [1, 0], [1, 6]);
    // Now on round 2 (scoring phase), undo round 2
    const result = await undoRound(game.id);

    expect(result.current_round).toBe(1);
    expect(result.phase).toBe('scoreboard');
  });
});

// ─── sync fields (quick-game-sync) ──────────────────────────────────────────

describe('test_create_game_has_client_game_id', () => {
  it('createGame returns a game with client_game_id matching id', async () => {
    const game = await createGame(makePlayers(), makeSettings());
    expect(game.client_game_id).toBe(game.id);
    expect(typeof game.client_game_id).toBe('string');
    expect(game.client_game_id).toMatch(/^game-/);
  });
});

describe('test_create_game_linked_room_defaults_null', () => {
  it('createGame sets linked_room to null by default', async () => {
    const game = await createGame(makePlayers(), makeSettings());
    expect(game.linked_room).toBeNull();
  });
});

describe('test_create_game_sync_pending_defaults_false', () => {
  it('createGame sets sync_pending to false by default', async () => {
    const game = await createGame(makePlayers(), makeSettings());
    expect(game.sync_pending).toBe(false);
  });
});

describe('test_create_game_default_must_lose_matches_server', () => {
  it('defaults must_lose to false (matching server default)', async () => {
    const game = await createGame(makePlayers(), {
      formula: 'kachuful_standard',
      rounds_per_set: 8,
      num_sets: 2,
      // must_lose intentionally omitted — should default to false
    });
    expect(game.settings.must_lose).toBe(false);
  });
});

describe('test_extend_game_preserves_completed_round', () => {
  it('extendGame does not overwrite the last completed round data', async () => {
    // Create a short game: 1 set × 1 round, must_lose off to simplify bidding
    const game = await createGame(makePlayers(), makeSettings({ rounds_per_set: 1, num_sets: 1, must_lose: false }));
    // Play round 1 (1 card dealt)
    await playRound(game.id, [0, 1], [0, 1]);
    await nextRound(game.id);

    // Verify round 1 has real scored data
    const { getRound } = await import('../../app/static/js/engine/store.js');
    const roundBefore = await getRound(game.id, 1);
    expect(roundBefore.status).toBe('complete');
    expect(roundBefore.scores).toBeDefined();

    // End game and extend
    await endGame(game.id);
    await extendGame(game.id);

    // Round 1 should still have its original scores
    const roundAfter = await getRound(game.id, 1);
    expect(roundAfter.status).toBe('complete');
    expect(roundAfter.scores).toEqual(roundBefore.scores);
    expect(roundAfter.bids).toEqual(roundBefore.bids);
  });
});
