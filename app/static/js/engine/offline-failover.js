/**
 * offline-failover.js — Transfer active server game to offline IDB storage.
 *
 * Used when all retry attempts fail. Preserves partial round data (bids/hands)
 * so the user can continue playing locally.
 */

import { saveGameAndRound } from './store.js';
import { NetworkError } from '../components/network-error.js';

function randomId() {
  return Math.random().toString(36).slice(2, 10);
}

/**
 * Transfer a server game to offline mode.
 *
 * Creates a local game + round in a single IDB transaction (atomic).
 * Returns the new local game ID for URL navigation.
 *
 * @param {Object} serverGame  The current game object from the server.
 * @param {Object} currentRoundData  Partial round data (bids, round_num, etc).
 * @param {string|null} shareCode  Playground share code for sync-back, or null.
 * @returns {Promise<string>}  The new local game ID.
 */
export async function transferToOffline(serverGame, currentRoundData, shareCode) {
  const localId = `game-${Date.now()}-${randomId()}`;

  const localGame = {
    id: localId,
    client_game_id: `failover-${serverGame.id}-${Date.now()}`,
    players: serverGame.players,
    settings: serverGame.settings,
    current_round: serverGame.current_round,
    total_rounds: serverGame.total_rounds,
    dealer_index: serverGame.dealer_index,
    phase: serverGame.phase,
    status: 'active',
    linked_room: shareCode || null,
    sync_pending: true,
    started_at: serverGame.started_at,
    source: 'failover',
  };

  const round = {
    game_id: localId,
    round_num: currentRoundData.round_num,
    bids: currentRoundData.bids || {},
    hands_won: currentRoundData.hands_won || {},
    cards_dealt: currentRoundData.cards_dealt,
    trump_suit: currentRoundData.trump_suit,
  };

  try {
    await saveGameAndRound(localGame, round);
  } catch (idbError) {
    throw new Error('Cannot play offline — private browsing not supported');
  }

  return localId;
}

/**
 * Check if an error is a network/timeout error (not a JS bug).
 *
 * @param {Error} error
 * @returns {boolean}
 */
export function isNetworkError(error) {
  if (error instanceof NetworkError) return true;
  if (error.name === 'AbortError') return true;
  if (error instanceof TypeError && error.message.includes('fetch')) return true;
  return false;
}
