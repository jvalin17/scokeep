/**
 * sync-back.js — Sync offline failover games back to server.
 *
 * Probes server health before attempting sync. Uses existing import endpoint.
 * Called on startup, online event, and screen navigation.
 */

import { getSyncPendingGames, saveGame } from './store.js';
import { syncOneGame } from './sync-import.js';

const HEALTH_TIMEOUT_MS = 5000;

/**
 * Attempt to sync all pending failover games back to the server.
 *
 * 1. Find games with sync_pending=true
 * 2. Probe /api/health to verify server is reachable
 * 3. For each game with a linked_room, call syncOneGame
 * 4. On success, clear sync_pending
 * 5. On failure, stop (don't keep trying if server is rejecting)
 *
 * @returns {Promise<{synced: number, failed: number, skipped?: boolean}>}
 */
export async function attemptSyncBack() {
  const pending = await getSyncPendingGames();
  const syncable = pending.filter(g => g.linked_room);

  if (syncable.length === 0) {
    return { synced: 0, failed: 0, skipped: true };
  }

  // Probe server health — don't trust navigator.onLine
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);
    await fetch('/api/health', {
      credentials: 'same-origin',
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
  } catch {
    return { synced: 0, failed: 0, skipped: true };
  }

  let synced = 0;
  let failed = 0;

  for (const game of syncable) {
    const result = await syncOneGame(game);
    if (result.success) {
      game.sync_pending = false;
      await saveGame(game);
      synced++;
    } else {
      failed++;
      break; // Stop on first failure
    }
  }

  return { synced, failed };
}
