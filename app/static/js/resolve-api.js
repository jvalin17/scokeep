/**
 * resolve-api.js — Routes game API calls to the correct backend.
 *
 * Online games (integer IDs from server) → api.js (server endpoints)
 * Quick games (string IDs starting with "game-") → game-api.js (local engine)
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
 * Returns the appropriate API module for the given game ID.
 * Uses dynamic imports so both modules are available but only one is loaded per call.
 *
 * @param {string|number} gameId
 * @returns {Promise<Object>} The API module (game-api.js or api.js)
 */
export async function getApi(gameId) {
  if (isLocalGame(gameId)) {
    return import('./game-api.js');
  }
  return import('./api.js');
}
