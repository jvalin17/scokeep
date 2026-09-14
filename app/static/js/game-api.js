/**
 * game-api.js — Unified game interface for screens.
 *
 * Delegates all logic and persistence to game-engine (IndexedDB), then fires
 * server-sync as a background side-effect for online backup.
 *
 * Screens should import from this module instead of engine/game-engine.js
 * so that server sync is always applied consistently.
 *
 * Public API mirrors game-engine.js exactly:
 *   createGame, getGame, submitBid, getBids, editBid
 *   startRound, enterRoundEnd, submitHands
 *   endRound, nextRound, endGame, extendGame
 *   getScoreboard, undoRound, confirmFinal
 */

import * as engine from './engine/game-engine.js';
import { syncRound, syncGameState } from './engine/server-sync.js';

// Re-export read-only helpers unchanged (no sync needed)
export const getGame = engine.getGame;
export const getBids = engine.getBids;
export const getScoreboard = engine.getScoreboard;

/**
 * Create a new game and persist it locally.
 *
 * @param {string[]} players
 * @param {Object}   settings
 * @returns {Promise<Object>} Created game.
 */
export async function createGame(players, settings) {
  const game = await engine.createGame(players, settings);
  syncGameState(game.id, game);
  return game;
}

/**
 * Submit a bid for a player and sync the round to the server.
 *
 * @param {string} gameId
 * @param {number} playerIndex
 * @param {number} value
 * @returns {Promise<Object>} Updated round.
 */
export async function submitBid(gameId, playerIndex, value) {
  const round = await engine.submitBid(gameId, playerIndex, value);
  syncRound(gameId, round);
  return round;
}

/**
 * Edit a player's existing bid and sync the round.
 *
 * @param {string} gameId
 * @param {number} playerIndex
 * @param {number} value
 * @returns {Promise<Object>} Updated round.
 */
export async function editBid(gameId, playerIndex, value) {
  const round = await engine.editBid(gameId, playerIndex, value);
  syncRound(gameId, round);
  return round;
}

/**
 * Start the round (transition to playing phase) and sync game state.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Updated game.
 */
export async function startRound(gameId) {
  const game = await engine.startRound(gameId);
  syncGameState(gameId, game);
  return game;
}

/**
 * Transition to round_end phase and sync game state.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Updated game.
 */
export async function enterRoundEnd(gameId) {
  const game = await engine.enterRoundEnd(gameId);
  syncGameState(gameId, game);
  return game;
}

/**
 * Submit hands won for a player and sync the round.
 *
 * @param {string} gameId
 * @param {number} playerIndex
 * @param {number} value
 * @returns {Promise<Object>} Updated round.
 */
export async function submitHands(gameId, playerIndex, value) {
  const round = await engine.submitHands(gameId, playerIndex, value);
  syncRound(gameId, round);
  return round;
}

/**
 * Score the round and sync both round and game state.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Scored round.
 */
export async function endRound(gameId) {
  const round = await engine.endRound(gameId);
  const game = await engine.getGame(gameId);
  syncRound(gameId, round);
  syncGameState(gameId, game);
  return round;
}

/**
 * Advance to next round and sync game state.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Updated game.
 */
export async function nextRound(gameId) {
  const game = await engine.nextRound(gameId);
  syncGameState(gameId, game);
  return game;
}

/**
 * Finish the game and sync state.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Updated game.
 */
export async function endGame(gameId) {
  const game = await engine.endGame(gameId);
  syncGameState(gameId, game);
  return game;
}

/**
 * Extend the game with another set and sync state.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Updated game.
 */
export async function extendGame(gameId) {
  const game = await engine.extendGame(gameId);
  syncGameState(gameId, game);
  return game;
}

/**
 * Undo the last round and sync state.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Updated game.
 */
export async function undoRound(gameId) {
  const game = await engine.undoRound(gameId);
  syncGameState(gameId, game);
  return game;
}

/**
 * Confirm the game is final and sync state.
 *
 * @param {string} gameId
 * @returns {Promise<Object>} Updated game.
 */
export async function confirmFinal(gameId) {
  const game = await engine.confirmFinal(gameId);
  syncGameState(gameId, game);
  return game;
}
