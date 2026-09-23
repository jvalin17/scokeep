/**
 * sync-manager.js — Single owner of server sync for IDB-first games.
 *
 * Gameplay writes IndexedDB first. This module POSTs completed rounds and
 * finished games in the background, with a mutex so syncs never overlap.
 */

import { logger } from '../components/logger.js';
import {
  saveGame, saveRound, getRoundsForGame,
  getFinishedGames, getSyncPendingGames as storeGetSyncPendingGames,
  saveSyncQueueItem, getSyncQueue, deleteSyncQueueItem,
} from './store.js';

const SYNC_TIMEOUT_MS = 15000;
const HEALTH_TIMEOUT_MS = 5000;

class SyncManager {
  #syncing = false;
  #queue = [];

  // ─── Public API ─────────────────────────────────────────

  static isLocalId(gameId) {
    return typeof gameId === 'string' && gameId.startsWith('game-');
  }

  isOnline() {
    return navigator.onLine;
  }

  async syncRound(serverGameId, round) {
    return this.#withLock('syncRound', () => this.#doSyncRound(serverGameId, round));
  }

  async syncGame(game) {
    return this.#withLock('syncGame', () => this.#doSyncGame(game));
  }

  async syncPending(shareCode = null) {
    return this.#withLock('syncPending', () => this.#doSyncPending(shareCode));
  }

  async retrySyncQueue() {
    return this.#withLock('retrySyncQueue', () => this.#doRetrySyncQueue());
  }

  resetForTesting() {
    this.#syncing = false;
    this.#queue = [];
  }

  async idleForTesting() {
    const deadline = Date.now() + 2000;
    while (this.#syncing || this.#queue.length > 0) {
      if (Date.now() > deadline) {
        this.#syncing = false;
        this.#queue = [];
        break;
      }
      await new Promise((resolve) => setTimeout(resolve, 5));
    }
  }

  // ─── Private: sync lock ─────────────────────────────────

  async #withLock(name, operation) {
    if (this.#syncing) {
      this.#log('info', 'lock', `${name} queued behind active sync`);
      return new Promise((resolve, reject) => {
        this.#queue.push(() => operation().then(resolve, reject));
      });
    }
    this.#syncing = true;
    this.#log('info', 'lock', `${name} acquired`);
    try {
      return await operation();
    } finally {
      // Drain while still holding the lock so a third sync cannot overlap.
      while (this.#queue.length > 0) {
        const next = this.#queue.shift();
        try {
          await next();
        } catch {
          // Rejection already forwarded to the waiter's promise.
        }
      }
      this.#syncing = false;
    }
  }

  // ─── Private: implementations ───────────────────────────

  async #doSyncRound(serverGameId, round) {
    if (!this.isOnline()) {
      await saveSyncQueueItem(serverGameId, round);
      this.#log('info', 'syncRound', `round ${round.round_num} skipped — offline, queued`);
      return { success: false, reason: 'offline' };
    }
    try {
      const response = await this.#postWithTimeout(
        `/api/game/${serverGameId}/sync-round`,
        round,
      );
      if (response.ok) {
        round.synced = true;
        await saveRound(round);
        this.#log('info', 'syncRound', `round ${round.round_num} synced to game ${serverGameId}`);
        return { success: true };
      }
      await saveSyncQueueItem(serverGameId, round);
      this.#log('warn', 'syncRound', `round ${round.round_num} failed (${response.status}), queued`);
      return { success: false, status: response.status };
    } catch (error) {
      await saveSyncQueueItem(serverGameId, round);
      this.#log('warn', 'syncRound', `round ${round.round_num} error: ${error.message}, queued`);
      return { success: false, error: error.message };
    }
  }

  async #doSyncGame(game) {
    const shareCode = game.linked_room;
    if (!shareCode) return { success: false, error: 'No linked room' };
    if (!this.isOnline()) return { success: false, reason: 'offline' };

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

      const response = await this.#postWithTimeout(
        `/api/game/${shareCode}/import`,
        payload,
      );

      if (response.ok) {
        game.sync_pending = false;
        await saveGame(game);
        this.#log('info', 'syncGame', `game synced: ${rounds.length} rounds to ${shareCode}`);
        return { success: true };
      }
      this.#log('warn', 'syncGame', `game sync failed (${response.status})`);
      return {
        success: false,
        status: response.status,
        error: `Server returned ${response.status}`,
      };
    } catch (error) {
      this.#log('warn', 'syncGame', `game sync error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  async #doSyncPending(shareCode) {
    this.#log('info', 'syncPending', 'checking pending games...');
    const allPending = shareCode
      ? await this.#getPendingForRoom(shareCode)
      : await storeGetSyncPendingGames();

    const syncable = allPending.filter(game => game.linked_room);
    const unsyncable = allPending.filter(game => !game.linked_room);

    for (const game of unsyncable) {
      game.sync_pending = false;
      await saveGame(game);
    }

    if (syncable.length === 0) {
      return { synced: 0, failed: 0, skipped: true, cleared: unsyncable.length };
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);
      const health = await fetch('/api/health', {
        credentials: 'same-origin',
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      if (!health.ok) {
        this.#log('warn', 'syncPending', `health probe failed (${health.status}) — skipping sync`);
        return { synced: 0, failed: 0, skipped: true };
      }
    } catch {
      this.#log('warn', 'syncPending', 'health probe failed — skipping sync');
      return { synced: 0, failed: 0, skipped: true };
    }

    let synced = 0;
    let failed = 0;

    for (const game of syncable) {
      const result = await this.#doSyncGame(game);
      if (result.success) {
        synced++;
      } else if (result.status >= 400 && result.status < 500) {
        game.sync_pending = false;
        game.sync_failed = true;
        await saveGame(game);
        failed++;
      } else {
        failed++;
        break;
      }
    }

    this.#log('info', 'syncPending', `${synced} synced, ${failed} failed, ${unsyncable.length} cleared`);
    return { synced, failed, cleared: unsyncable.length };
  }

  async #doRetrySyncQueue() {
    const queue = await getSyncQueue();
    for (const item of queue) {
      try {
        const response = await this.#postWithTimeout(
          `/api/game/${item.game_id}/sync-round`,
          item.round,
        );
        if (response.ok) {
          await deleteSyncQueueItem(item.id);
          this.#log('info', 'retrySyncQueue', `queued round synced and removed`);
        }
      } catch {
        this.#log('warn', 'retrySyncQueue', 'retry failed — stopping');
        break;
      }
    }
  }

  // ─── Private: helpers ───────────────────────────────────

  async #postWithTimeout(url, body) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), SYNC_TIMEOUT_MS);
    try {
      return await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        credentials: 'same-origin',
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timeoutId);
    }
  }

  async #getPendingForRoom(shareCode) {
    const allFinished = await getFinishedGames(100);
    return allFinished.filter(
      game => game.linked_room === shareCode && game.sync_pending === true,
    );
  }

  #log(level, action, detail) {
    logger[level]('sync', `${action}: ${detail}`);
  }
}

export const syncManager = new SyncManager();
export const isLocalId = SyncManager.isLocalId;

export function retrySyncQueue() {
  return syncManager.retrySyncQueue();
}

export async function syncOneGame(game) {
  return syncManager.syncGame(game);
}

export async function getSyncPendingGames(shareCode) {
  const allFinished = await getFinishedGames(100);
  return allFinished.filter(
    (game) => game.linked_room === shareCode && game.sync_pending === true,
  );
}

export async function attemptSyncBack(shareCode = null) {
  return syncManager.syncPending(shareCode);
}
