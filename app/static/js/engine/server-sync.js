/**
 * server-sync.js — Fire-and-forget server backup for offline-first game data.
 *
 * Sends round and game-state snapshots to the server so the ML pipeline has
 * a reliable record. On failure, rounds are queued in IDB for later retry.
 */

import { saveSyncQueueItem, getSyncQueue, deleteSyncQueueItem } from './store.js';

/**
 * Sync a completed round to the server.
 * On failure, queues the round in IDB for retry.
 *
 * @param {string} gameId
 * @param {Object} round  Full round object (round_num, bids, hands_won, scores, …)
 */
export function syncRound(gameId, round) {
  if (!navigator.onLine) {
    saveSyncQueueItem(gameId, round).catch(() => {});
    return;
  }
  fetch(`/api/game/${gameId}/sync-round`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(round),
    credentials: 'same-origin',
  }).catch(() => {
    saveSyncQueueItem(gameId, round).catch(() => {});
  });
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
  }).catch(() => {}); // fire-and-forget (state is ephemeral)
}

/**
 * Retry all queued round syncs. Called on online event or after a successful sync.
 */
export async function retrySyncQueue() {
  const queue = await getSyncQueue();
  for (const item of queue) {
    try {
      const res = await fetch(`/api/game/${item.game_id}/sync-round`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item.round),
        credentials: 'same-origin',
      });
      if (res.ok) {
        await deleteSyncQueueItem(item.id);
      }
    } catch {
      // Still offline or server error — leave in queue for next retry
      break;
    }
  }
}
