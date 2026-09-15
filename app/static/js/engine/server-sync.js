/**
 * server-sync.js — Fire-and-forget server backup for offline-first game data.
 *
 * Sends round and game-state snapshots to the server so the ML pipeline has
 * a reliable record. All errors are silently swallowed; the game works
 * entirely without a successful sync.
 */

/**
 * Sync a completed round to the server.
 *
 * @param {string} gameId
 * @param {Object} round  Full round object (round_num, bids, hands_won, scores, …)
 */
export function syncRound(gameId, round) {
  if (!navigator.onLine) return;
  fetch(`/api/game/${gameId}/sync-round`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(round),
    credentials: 'same-origin',
  }).catch(() => {}); // fire-and-forget
}

/**
 * Sync the current game phase/state to the server.
 *
 * @param {string} gameId
 * @param {Object} game  Game object with phase, current_round, dealer_index, status.
 */
export function syncGameState(gameId, game) {
  if (!navigator.onLine) return;
  fetch(`/api/game/${gameId}/sync-state`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      phase: game.phase,
      current_round: game.current_round,
      dealer_index: game.dealer_index,
      status: game.status,
    }),
    credentials: 'same-origin',
  }).catch(() => {}); // fire-and-forget
}
