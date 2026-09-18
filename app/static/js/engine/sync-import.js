/**
 * sync-import.js — Sync offline Quick Games to server via import endpoint.
 *
 * Handles: POST /api/game/{share_code}/import for linked Quick Games.
 * Separate from server-sync.js which handles round-level fire-and-forget syncs.
 */

import { getRoundsForGame, getFinishedGames, saveGame } from './store.js';

/**
 * Sync a single linked Quick Game to the server.
 *
 * @param {Object} game  Game object with linked_room, client_game_id, etc.
 * @returns {Promise<{success: boolean, error?: string}>}
 */
export async function syncOneGame(game) {
  const shareCode = game.linked_room;
  if (!shareCode) return { success: false, error: 'No linked room' };

  try {
    const rounds = await getRoundsForGame(game.id);
    const payload = {
      client_game_id: game.client_game_id,
      started_at: game.started_at,
      finished_at: game.finished_at,
      players: game.players,
      settings: game.settings,
      rounds: rounds.map(round => ({
        round_num: round.round_num,
        bids: round.bids,
        hands_won: round.hands_won,
        cards_dealt: round.cards_dealt,
        trump_suit: round.trump_suit,
      })),
    };

    const response = await fetch(`/api/game/${shareCode}/import`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      credentials: 'same-origin',
    });

    if (!response.ok) {
      return { success: false, error: `Server returned ${response.status}` };
    }

    // Mark as synced in IDB
    game.sync_pending = false;
    await saveGame(game);
    return { success: true };
  } catch (error) {
    console.warn('Sync import failed:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Get all finished games that are pending sync for a specific room.
 *
 * @param {string} shareCode  Room share_code to filter by.
 * @returns {Promise<Object[]>}  Array of pending game objects.
 */
export async function getSyncPendingGames(shareCode) {
  const allFinished = await getFinishedGames(100);
  return allFinished.filter(
    game => game.linked_room === shareCode && game.sync_pending === true,
  );
}
