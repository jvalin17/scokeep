/**
 * game-api.js — Unified game interface for screens.
 *
 * Delegates all logic and persistence to game-engine (IndexedDB), then fires
 * SyncManager as a background side-effect for online backup.
 *
 * Screens should import from this module instead of engine/game-engine.js
 * so that server sync is always applied consistently.
 *
 * Public API mirrors api.js shape for drop-in replacement by game screens:
 *   createGame, getGame, getBids, getScoreboard
 *   submitBid, editBid, startRound, enterRoundEnd, submitHands
 *   endRound, nextRound, endGame, extendGame
 *   undoRound, confirmFinal
 *   guardPhase, resyncGame, loadGameFromServer
 *   enterRescore, rescoreRound, enterReview
 */

import * as engine from './engine/game-engine.js';
import { saveGame as storeSaveGame, saveRound as storeSaveRound, getRound as storeGetRound } from './engine/store.js';
import { syncManager } from './engine/sync-manager.js';
import { logger } from './components/logger.js';

/**
 * Quiet finalize for a server game — no reconnect banner, no long retries.
 * POST /end (phase=review, status still active) then POST /confirm-final
 * (status=finished). Without confirm-final, lobby Resume stays forever.
 */
async function finalizeServerGameQuiet(serverGameId) {
  const endResponse = await fetchWithTimeout(`/api/game/${serverGameId}/end`, {
    method: 'POST',
    credentials: 'same-origin',
  });
  // 409 = already finished — treat as done
  if (endResponse.status === 409) {
    return { already_finished: true };
  }
  if (!endResponse.ok) {
    throw new Error(`Server /end returned ${endResponse.status}`);
  }

  const confirmResponse = await fetchWithTimeout(
    `/api/game/${serverGameId}/confirm-final`,
    {
      method: 'POST',
      credentials: 'same-origin',
    },
  );
  if (confirmResponse.status === 409) {
    // Already past review (e.g. prior partial finalize) — check via re-end
    return { already_finished: true };
  }
  if (!confirmResponse.ok) {
    throw new Error(`Server /confirm-final returned ${confirmResponse.status}`);
  }
  return confirmResponse.json().catch(() => ({}));
}

const PHASE_ROUTES = {
  bidding: 'bid',
  playing: 'play',
  round_end: 'roundend',
  scoring: 'scoreboard',
  scoreboard: 'scoreboard',
  review: 'review',
  final: 'final',
  finished: 'scoreboard',
};

const FETCH_TIMEOUT_MS = 15000;

function fetchWithTimeout(url, options = {}) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
    return fetch(url, { ...options, signal: controller.signal })
        .finally(() => clearTimeout(timeoutId));
}

// ─── server bridge ────────────────────────────────────────────────────────────

/**
 * Fetch a game and all its rounds from the server and save them to IndexedDB.
 * Called when a server-created game is not yet in local storage.
 *
 * @param {string|number} gameId
 * @returns {Promise<Object>} The game object.
 */
export async function loadGameFromServer(gameId) {
  const resp = await fetchWithTimeout(`/api/game/${gameId}`, { credentials: 'same-origin' });
  if (!resp.ok) throw new Error('Failed to load game from server');
  const game = await resp.json();

  const roundsResp = await fetchWithTimeout(`/api/game/${gameId}/history`, { credentials: 'same-origin' });
  const roundsData = roundsResp.ok ? await roundsResp.json() : [];

  // Also fetch the current round (may be in bidding/playing — not in history)
  try {
    const bidsResp = await fetchWithTimeout(`/api/game/${gameId}/bids`, { credentials: 'same-origin' });
    if (bidsResp.ok) {
      const currentRound = await bidsResp.json();
      if (currentRound && currentRound.round_num) {
        roundsData.push(currentRound);
      }
    }
  } catch { /* current round may not exist yet */ }

  game.server_game_id = game.server_game_id ?? game.id;
  await storeSaveGame(game);
  for (const round of roundsData) {
    await storeSaveRound(round);
  }
  return game;
}

// ─── navigation helpers ───────────────────────────────────────────────────────

/**
 * Guard: ensure the local game phase matches expectedPhase.
 * If the game is not in IndexedDB and we are online, fetch it from the server.
 * Redirects to the correct screen if phase mismatches.
 *
 * @param {string|number} gameId
 * @param {string} expectedPhase
 * @returns {Promise<Object|null>} game object, or null if redirected.
 */
export async function guardPhase(gameId, expectedPhase) {
  let game = await engine.getGame(gameId);
  if (!game && navigator.onLine) {
    try {
      game = await loadGameFromServer(gameId);
    } catch { /* fall through — will be null */ }
  }
  if (!game) return null;

  if (game.phase !== expectedPhase) {
    const route = PHASE_ROUTES[game.phase] || 'scoreboard';
    window.location.hash = `${route}/${gameId}`;
    return null;
  }
  return game;
}

/**
 * Re-sync: load game state and navigate to the correct screen.
 *
 * @param {string|number} gameId
 * @returns {Promise<Object>} game object.
 */
export async function resyncGame(gameId) {
  let game = await engine.getGame(gameId);
  if (!game && navigator.onLine) {
    game = await loadGameFromServer(gameId);
  }
  if (!game) throw new Error(`Game not found: ${gameId}`);
  const route = PHASE_ROUTES[game.phase] || 'scoreboard';
  window.location.hash = `${route}/${gameId}`;
  return game;
}

// ─── re-score / review helpers ────────────────────────────────────────────────

/**
 * Enter rescore mode: reset current round scores and status back to round_end
 * so hands can be re-entered, then transition the game phase to round_end.
 *
 * @param {string|number} gameId
 * @returns {Promise<Object>} Updated game.
 */
export async function enterRescore(gameId) {
  const game = await engine.getGame(gameId);
  if (!game) throw new Error(`Game not found: ${gameId}`);
  const round = await storeGetRound(game.id, game.current_round);
  if (round) {
    round.scores = {};
    round.status = 'round_end';
    await storeSaveRound(round);
  }
  game.phase = 'round_end';
  await storeSaveGame(game);
  return game;
}

/**
 * Prepare a specific round for rescoring by setting its status back to active
 * and transitioning the game to round_end phase.
 *
 * @param {string|number} gameId
 * @param {number} roundNum
 * @returns {Promise<Object>} Updated game.
 */
export async function rescoreRound(gameId, roundNum) {
  // Reset the targeted round's status so endRound will re-score it.
  const game = await engine.getGame(gameId);
  if (!game) throw new Error(`Game not found: ${gameId}`);

  // Load the round from store and set it back to active.
  const round = await storeGetRound(gameId, roundNum);
  if (round) {
    round.status = 'active';
    await storeSaveRound(round);
  }

  // Set current_round to the round being rescored so endRound targets it.
  game.current_round = roundNum;
  game.phase = 'round_end';
  await storeSaveGame(game);
  return game;
}

/**
 * Enter the review phase.
 *
 * @param {string|number} gameId
 * @returns {Promise<Object>} Updated game.
 */
export async function enterReview(gameId) {
  const game = await engine.getGame(gameId);
  if (!game) throw new Error(`Game not found: ${gameId}`);
  game.phase = 'review';
  await storeSaveGame(game);
  return game;
}

// ─── read-only helpers ────────────────────────────────────────────────────────

/**
 * Get a game by ID from IndexedDB, with server fallback if not found locally.
 *
 * @param {string|number} gameId
 * @returns {Promise<Object|null>}
 */
export async function getGame(gameId) {
  let game = await engine.getGame(gameId);
  if (!game && navigator.onLine) {
    game = await loadGameFromServer(gameId);
  }
  return game;
}

/**
 * Get the current round data (bids, hands_won, cards_dealt, etc.).
 * Named getBids for API compatibility with api.js; returns full round object.
 *
 * @param {string|number} gameId
 * @returns {Promise<Object>} Round object with bids, hands_won, cards_dealt, etc.
 */
export async function getBids(gameId) {
  const game = await engine.getGame(gameId);
  if (!game) throw new Error(`Game not found: ${gameId}`);
  const round = await storeGetRound(gameId, game.current_round);
  if (!round) throw new Error(`Round not found: game=${gameId} round=${game.current_round}`);
  return round;
}

/**
 * Get the scoreboard (totals + per-round data), with server fallback if local
 * data is empty (game may not be in IndexedDB yet).
 *
 * @param {string|number} gameId
 * @returns {Promise<{totals: Object, rounds: Array}>}
 */
export async function getScoreboard(gameId) {
  let result = await engine.getScoreboard(gameId);
  if ((!result || !result.rounds || result.rounds.length === 0) && navigator.onLine) {
    // Try server — game might not be in IndexedDB yet
    try {
      const resp = await fetchWithTimeout(`/api/game/${gameId}/scoreboard`, { credentials: 'same-origin' });
      if (resp.ok) return await resp.json();
    } catch { /* fall through to local result */ }
  }
  return result || { totals: {}, rounds: [] };
}

/**
 * Create a new game and persist it locally.
 *
 * @param {string[]} players
 * @param {Object}   settings
 * @returns {Promise<Object>} Created game.
 */
export async function createGame(players, settings) {
  return engine.createGame(players, settings);
}

/**
 * Create a local IDB mirror of a server-created room game.
 * Rounds sync via sync-round to server_game_id; sync_pending stays false
 * so confirmFinal does not POST /import (which would duplicate the room game).
 *
 * @param {number|string} serverGameId
 * @param {string[]} players
 * @param {Object} settings
 * @param {string} shareCode
 * @returns {Promise<Object>} Local game with server_game_id set.
 */
export async function createOnlineGame(serverGameId, players, settings, shareCode) {
  const game = await engine.createGame(players, {
    ...settings,
    linked_room: shareCode,
  });
  game.server_game_id = serverGameId;
  game.sync_pending = false;
  await storeSaveGame(game);
  return game;
}

/**
 * Submit a bid for a player (IndexedDB only — no per-tap sync).
 *
 * @param {string} gameId
 * @param {number} playerIndex
 * @param {number} value
 * @returns {Promise<Object>} Updated round.
 */
export async function submitBid(gameId, playerIndex, value) {
  return engine.submitBid(gameId, playerIndex, value);
}

/**
 * Edit a player's existing bid (IndexedDB only — no per-tap sync).
 *
 * @param {string} gameId
 * @param {number} playerIndex
 * @param {number} value
 * @returns {Promise<Object>} Updated round.
 */
export async function editBid(gameId, playerIndex, value) {
  return engine.editBid(gameId, playerIndex, value);
}

/**
 * Start the round (transition to playing phase). IndexedDB only.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Updated game.
 */
export async function startRound(gameId) {
  return engine.startRound(gameId);
}

/**
 * Transition to round_end phase. IndexedDB only.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Updated game.
 */
export async function enterRoundEnd(gameId) {
  return engine.enterRoundEnd(gameId);
}

/**
 * Submit hands won for a player. IndexedDB only.
 *
 * @param {string} gameId
 * @param {number} playerIndex
 * @param {number} value
 * @returns {Promise<Object>} Updated round.
 */
export async function submitHands(gameId, playerIndex, value) {
  return engine.submitHands(gameId, playerIndex, value);
}

/**
 * Score the round; background syncRound when server_game_id is set.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Scored round.
 */
export async function endRound(gameId) {
  const round = await engine.endRound(gameId);
  const game = await engine.getGame(gameId);
  if (game && game.server_game_id) {
    syncManager.syncRound(game.server_game_id, round);
  }
  return round;
}

/**
 * Advance to next round. IndexedDB only.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Updated game.
 */
export async function nextRound(gameId) {
  return engine.nextRound(gameId);
}

/**
 * Finish the game (status=finished, phase=review). IndexedDB only.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Updated game.
 */
export async function endGame(gameId) {
  return engine.endGame(gameId);
}

/**
 * Extend the game with another set. IndexedDB only.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Updated game.
 */
export async function extendGame(gameId) {
  return engine.extendGame(gameId);
}

/**
 * Undo the last round. IndexedDB only.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Updated game.
 */
export async function undoRound(gameId) {
  return engine.undoRound(gameId);
}

/**
 * Confirm the game is final, then background-sync.
 * Online room games: retry queued rounds + POST /end then /confirm-final
 * so the server game leaves "active" (otherwise lobby Resume never clears).
 * Offline Quick Games: import via syncGame when sync_pending.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Updated game.
 */
export async function confirmFinal(gameId) {
  const game = await engine.confirmFinal(gameId);

  if (game.server_game_id) {
    syncManager.retrySyncQueue().catch(error =>
      logger.warn('sync', `confirmFinal queue retry failed: ${error.message}`),
    );
    finalizeServerGameQuiet(game.server_game_id)
      .then(async () => {
        const latest = await engine.getGame(gameId);
        if (latest?.server_end_pending) {
          latest.server_end_pending = false;
          await storeSaveGame(latest);
        }
      })
      .catch(async (error) => {
        logger.warn('sync', `confirmFinal server finalize failed: ${error.message}`);
        const latest = await engine.getGame(gameId);
        if (latest) {
          latest.server_end_pending = true;
          await storeSaveGame(latest);
        }
      });
  } else if (game.linked_room && game.sync_pending) {
    syncManager.syncGame(game).catch(error =>
      logger.warn('sync', `confirmFinal auto-sync failed: ${error.message}`),
    );
  }

  return game;
}
