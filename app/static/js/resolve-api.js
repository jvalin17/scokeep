/**
 * resolve-api.js — Routes game API calls to the local engine.
 *
 * All active gameplay uses game-api.js (IndexedDB first + SyncManager).
 * api.js remains for room/auth/stats, not in-game taps.
 */

/**
 * Returns true if the game ID belongs to a local/quick game.
 * Local game IDs are strings starting with "game-".
 * Server game IDs are integers or numeric strings.
 *
 * @param {*} gameId
 * @returns {boolean}
 */
export function isLocalGame(gameId) {
  return typeof gameId === 'string' && gameId.startsWith('game-');
}

/**
 * Returns the game-api module for every game id.
 * Online room games are mirrored in IndexedDB; screens always write locally.
 *
 * @param {string|number} gameId
 * @returns {Promise<Object>} The game-api.js module
 */
export async function getApi(gameId) {
  return import('./game-api.js');
}
