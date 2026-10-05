/**
 * game-engine.js — Game lifecycle orchestrator.
 *
 * Ties together scoring, trump, validation, phase, and store into a unified
 * game lifecycle. Every operation validates, computes, and persists to IndexedDB.
 *
 * Public API:
 *   createGame, getGame, submitBid, getBids, editBid
 *   startRound, enterRoundEnd, submitHands
 *   endRound, nextRound, endGame, extendGame
 *   getScoreboard, undoRound, confirmFinal, ensureActiveRound
 */

import { calculateRoundScores } from './scoring.js';
import { getTrumpForRound, getCardsForRound } from './trump.js';
import { validateBid } from './bid.js';
import { validateHands } from './hands.js';
import { advanceRound, extendGame as phaseExtendGame } from './phase.js';
import { computeScoreboard } from './scoreboard.js';
import {
  saveGame,
  getGame as storeGetGame,
  saveRound,
  getRound,
  getRoundsForGame,
  commitUndoRound,
} from './store.js';

// ─── internal helpers ────────────────────────────────────────────────────────

/**
 * Generate a short random string ID.
 * @returns {string}
 */
function _generateId() {
  return `game-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

/**
 * Load game; throw if not found.
 * @param {string} gameId
 * @returns {Promise<Object>}
 */
async function _requireGame(gameId) {
  const game = await storeGetGame(gameId);
  if (!game) throw new Error(`Game not found: ${gameId}`);
  return game;
}

/**
 * Load round for the game's current_round; throw if not found.
 * @param {Object} game
 * @returns {Promise<Object>}
 */
async function _requireRound(game) {
  const round = await getRound(game.id, game.current_round);
  if (!round) throw new Error(`Round not found: game=${game.id} round=${game.current_round}`);
  return round;
}

/**
 * Create a fresh round record for the given game/round number.
 * @param {Object} game
 * @param {number} roundNum
 * @returns {Object}
 */
function _makeRound(game, roundNum) {
  const rps = game.settings.rounds_per_set ?? 8;
  return {
    game_id: game.id,
    round_num: roundNum,
    cards_dealt: getCardsForRound(roundNum, rps),
    trump_suit: getTrumpForRound(roundNum),
    bids: {},
    hands_won: {},
    scores: {},
    status: 'active',
  };
}

// ─── public API ──────────────────────────────────────────────────────────────

/**
 * Create a new game, persist it, and create round 1.
 *
 * @param {string[]} players  Player name array.
 * @param {Object}   settings Game settings.
 * @param {string}   [settings.formula='kachuful_standard']
 * @param {boolean}  [settings.must_lose=true]
 * @param {number}   [settings.rounds_per_set=8]
 * @param {number}   [settings.num_sets=3]
 * @returns {Promise<Object>} The created game object.
 */
export async function createGame(players, settings) {
  const roundsPerSet = settings.rounds_per_set ?? 8;
  const numSets = settings.num_sets ?? 3;
  const gameType = settings.game_type ?? 'kachuful';
  const startPhase = gameType === 'scoresheet' ? 'entry' : 'bidding';
  const totalRounds = gameType === 'scoresheet' ? 500 : roundsPerSet * numSets;

  const gameId = _generateId();
  const game = {
    id: gameId,
    client_game_id: gameId,
    linked_room: settings.linked_room ?? null,
    sync_pending: settings.linked_room ? true : false,
    players,
    settings: {
      game_type: gameType,
      mode: settings.mode ?? 'rookie',
      appearance: settings.appearance ?? 'interactive',
      scoring_formula: settings.scoring_formula ?? settings.formula ?? 'kachuful_standard',
      must_lose: settings.must_lose ?? false,
      rounds_per_set: roundsPerSet,
      num_sets: numSets,
      ...(gameType === 'scoresheet'
        ? {
            label: settings.label ?? '',
            winner: settings.winner ?? 'highest',
            show_totals: settings.show_totals !== false,
            allow_negatives: settings.allow_negatives === true,
          }
        : {}),
    },
    current_round: 1,
    total_rounds: totalRounds,
    phase: startPhase,
    dealer_index: 0,
    status: 'active',
    started_at: new Date().toISOString(),
    finished_at: null,
  };

  await saveGame(game);
  const round = _makeRound(game, 1);
  await saveRound(round);
  return game;
}

/**
 * Retrieve a game by id.
 * @param {string} gameId
 * @returns {Promise<Object|null>}
 */
export async function getGame(gameId) {
  return storeGetGame(gameId);
}

/**
 * Submit a bid for a player in the current round.
 *
 * @param {string} gameId
 * @param {number} playerIndex
 * @param {number} value
 * @returns {Promise<Object>} Updated round object.
 */
export async function submitBid(gameId, playerIndex, value) {
  const game = await _requireGame(gameId);
  const round = await _requireRound(game);

  const error = validateBid(round.bids, playerIndex, value, {
    mustLose: game.settings.must_lose,
    cardsDeal: round.cards_dealt,
    playerCount: game.players.length,
  });
  if (error) throw new Error(error);

  round.bids[String(playerIndex)] = value;
  await saveRound(round);
  return round;
}

/**
 * Return the bids map for the current round.
 *
 * @param {string} gameId
 * @returns {Promise<Object.<string, number>>}
 */
export async function getBids(gameId) {
  const game = await _requireGame(gameId);
  const round = await _requireRound(game);
  return round.bids;
}

/**
 * Edit (overwrite) a player's existing bid.
 *
 * @param {string} gameId
 * @param {number} playerIndex
 * @param {number} value
 * @returns {Promise<Object>} Updated round object.
 */
export async function editBid(gameId, playerIndex, value) {
  const game = await _requireGame(gameId);
  const round = await _requireRound(game);

  // Remove the existing bid so validateBid doesn't see it as a duplicate.
  const bidsWithout = { ...round.bids };
  delete bidsWithout[String(playerIndex)];

  const error = validateBid(bidsWithout, playerIndex, value, {
    mustLose: game.settings.must_lose,
    cardsDeal: round.cards_dealt,
    playerCount: game.players.length,
  });
  if (error) throw new Error(error);

  round.bids[String(playerIndex)] = value;
  await saveRound(round);
  return round;
}

/**
 * Transition the game to the playing phase.
 * Call after all bids have been submitted.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Updated game object.
 */
export async function startRound(gameId) {
  const game = await _requireGame(gameId);
  game.phase = 'playing';
  await saveGame(game);
  return game;
}

/**
 * Transition the game to the round_end phase (cards played, entering results).
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Updated game object.
 */
export async function enterRoundEnd(gameId) {
  const game = await _requireGame(gameId);
  game.phase = 'round_end';
  await saveGame(game);
  return game;
}

/**
 * Submit hands won for a player in the current round.
 *
 * @param {string} gameId
 * @param {number} playerIndex
 * @param {number} value
 * @returns {Promise<Object>} Updated round object.
 */
export async function submitHands(gameId, playerIndex, value) {
  const game = await _requireGame(gameId);
  const round = await _requireRound(game);

  const error = validateHands(round.hands_won, playerIndex, value, round.cards_dealt);
  if (error) throw new Error(error);

  round.hands_won[String(playerIndex)] = value;
  await saveRound(round);
  return round;
}

/**
 * Score the current round and mark it complete.
 * Transitions game to 'scoreboard' phase.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Updated round object with computed scores.
 */
export async function endRound(gameId) {
  const game = await _requireGame(gameId);
  const round = await _requireRound(game);

  const formula = game.settings.scoring_formula ?? game.settings.formula ?? 'kachuful_standard';
  round.scores = calculateRoundScores(round.bids, round.hands_won, formula);
  round.status = 'complete';

  // Review-phase rescore returns to review (parity with server _review_rescore).
  if (game.settings?._review_rescore) {
    game.settings = Object.fromEntries(
      Object.entries(game.settings).filter(([key]) => key !== '_review_rescore'),
    );
    game.phase = 'review';
  } else {
    game.phase = 'scoreboard';
  }

  await saveRound(round);
  await saveGame(game);
  return round;
}

/**
 * Lock a Scoresheet round: write direct scores, mark complete, show board or intermission.
 * No network — callers sync after this returns.
 *
 * @param {string} gameId
 * @param {Object.<string|number, number>} scoresByPlayerIndex
 * @returns {Promise<Object>} Completed round.
 */
export async function lockScoresheetRound(gameId, scoresByPlayerIndex) {
  const game = await _requireGame(gameId);
  if ((game.settings?.game_type || 'kachuful') !== 'scoresheet') {
    throw new Error('lockScoresheetRound is only for Scoresheet games');
  }

  let round = await getRound(game.id, game.current_round);
  if (!round) {
    round = _makeRound(game, game.current_round);
  }

  const scores = {};
  for (const [key, value] of Object.entries(scoresByPlayerIndex)) {
    scores[String(key)] = Number(value);
  }
  if (Object.keys(scores).length !== game.players.length) {
    throw new Error('Scoresheet round requires a score for every player');
  }

  round.scores = scores;
  round.bids = {};
  round.hands_won = {};
  round.cards_dealt = 1;
  round.trump_suit = 'n/a';
  round.status = 'complete';

  const showTotals = game.settings?.show_totals !== false;
  game.phase = showTotals ? 'scoreboard' : 'intermission';

  await saveRound(round);
  await saveGame(game);
  return round;
}

/**
 * Advance to the next round (or enter review if all rounds are done).
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Updated game object.
 */
export async function nextRound(gameId) {
  const game = await _requireGame(gameId);
  const isScoresheet = (game.settings?.game_type || 'kachuful') === 'scoresheet';

  if (isScoresheet) {
    if (game.current_round >= game.total_rounds - 1) {
      game.total_rounds += 500;
    }
    game.current_round += 1;
    game.dealer_index = (game.dealer_index + 1) % game.players.length;
    game.phase = 'entry';
    await saveGame(game);
    const round = _makeRound(game, game.current_round);
    round.cards_dealt = 1;
    round.trump_suit = 'n/a';
    await saveRound(round);
    return game;
  }

  const advanced = advanceRound(game);

  await saveGame(advanced);

  // If we're still playing (not review), create the next round record.
  if (advanced.phase === 'bidding') {
    const round = _makeRound(advanced, advanced.current_round);
    await saveRound(round);
  }

  return advanced;
}

/**
 * Finish the game: set status=finished and phase=review for score review.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Updated game object.
 */
export async function endGame(gameId) {
  const game = await _requireGame(gameId);
  game.status = 'finished';
  game.phase = 'review';
  game.finished_at = new Date().toISOString();
  await saveGame(game);
  return game;
}

/**
 * Add another set of rounds to the game.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Updated game object.
 */
export async function extendGame(gameId) {
  const game = await _requireGame(gameId);
  const extended = phaseExtendGame(game);
  // Restore phase to bidding so the next round can start.
  extended.phase = 'bidding';
  await saveGame(extended);

  // Round creation happens in nextRound() after current_round is incremented.
  // Do NOT create a round here — it would overwrite the completed round's data.

  return extended;
}

/**
 * Compute the cumulative scoreboard from all completed rounds.
 *
 * @param {string} gameId
 * @returns {Promise<{totals: Object.<string, number>, rounds: Array<Object>}>}
 */
export async function getScoreboard(gameId) {
  const game = await _requireGame(gameId);
  const rounds = await getRoundsForGame(gameId);
  const scoredRounds = rounds.filter((r) => r.status === 'complete');
  return computeScoreboard(scoredRounds, game.players.length);
}

/**
 * Ensure an active round row exists for the game's current_round.
 * Used when bidding mounts after undo deleted the only round row.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Round object.
 */
export async function ensureActiveRound(gameId) {
  const game = await _requireGame(gameId);
  let round = await getRound(game.id, game.current_round);
  if (!round) {
    round = _makeRound(game, game.current_round);
    await saveRound(round);
  }
  return round;
}

/**
 * Undo the most recently completed round: delete it and step phase back.
 * Round 1 undo stays on round 1 in bidding and recreates an empty active round
 * so rebidding can continue. Later rounds return to the previous scoreboard.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Updated game object.
 */
export async function undoRound(gameId) {
  const game = await _requireGame(gameId);

  // Determine which round to undo.
  // If scoring/bidding for round N, undo round N-1 (already complete).
  // If round_end/playing for round N, undo round N itself.
  const roundToUndo = game.current_round;

  // Step back to the previous round (or stay at 1 if already round 1).
  // Dealer advances only on nextRound — so undoing round 1 must NOT rotate
  // (restart with the original dealer). Later undos reverse that advance.
  const wasAtRoundOne = game.current_round <= 1;
  if (game.current_round > 1) {
    game.current_round = game.current_round - 1;
    game.dealer_index =
      (game.dealer_index - 1 + game.players.length) % game.players.length;
  }
  const isScoresheet = (game.settings?.game_type || 'kachuful') === 'scoresheet';
  // Round 1 undo → back to entry/bidding. Later rounds → scoreboard of previous round.
  if (wasAtRoundOne) {
    game.phase = isScoresheet ? 'entry' : 'bidding';
  } else {
    game.phase = 'scoreboard';
  }

  // Undoing round 1 deletes the only round row; recreate an empty active round
  // so entry/bidding can continue (otherwise submitBid → "Round not found").
  const replacement =
    game.phase === 'bidding' || game.phase === 'entry'
      ? _makeRound(game, game.current_round)
      : null;
  if (replacement && isScoresheet) {
    replacement.cards_dealt = 1;
    replacement.trump_suit = 'n/a';
  }

  // Single IDB transaction (waits for oncomplete) so navigate→getBids cannot
  // race a still-open delete/put.
  await commitUndoRound(game, roundToUndo, replacement);

  return game;
}

/**
 * Confirm the game is complete (from review phase): set status=finished.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Updated game object.
 */
export async function confirmFinal(gameId) {
  const game = await _requireGame(gameId);
  game.phase = 'final';
  game.status = 'finished';
  await saveGame(game);
  return game;
}
