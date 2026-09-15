/**
 * IndexedDB game state store.
 *
 * Database: scokeep-local
 *
 * Store: games
 *   keyPath: id
 *   indexes: status, playground_id
 *
 * Store: rounds
 *   keyPath: [game_id, round_num]   (compound)
 *   indexes: game_id
 */

const DB_NAME = 'scokeep-local';
const DB_VERSION = 1;

/**
 * Normalize a game ID — hash URLs give strings but server IDs are integers.
 * IDB key lookup requires exact type match, so parse numeric strings to ints.
 */
function _normalizeId(id) {
  if (typeof id === 'string' && /^\d+$/.test(id)) return parseInt(id, 10);
  return id;
}

/** Cached DB connection (module-level singleton). */
let _db = null;

// ─── internal helpers ────────────────────────────────────────────────────────

/**
 * Return the active IDBFactory.
 * Using globalThis allows tests to swap indexedDB with a fresh IDBFactory.
 * @returns {IDBFactory}
 */
function _idb() {
  return globalThis.indexedDB;
}

/**
 * Open (or return the cached) database connection.
 * @returns {Promise<IDBDatabase>}
 */
function _open() {
  if (_db) return Promise.resolve(_db);

  return new Promise((resolve, reject) => {
    const req = _idb().open(DB_NAME, DB_VERSION);

    req.onupgradeneeded = (event) => {
      const db = event.target.result;

      // games store
      if (!db.objectStoreNames.contains('games')) {
        const games = db.createObjectStore('games', { keyPath: 'id' });
        games.createIndex('status', 'status', { unique: false });
        games.createIndex('playground_id', 'playground_id', { unique: false });
      }

      // rounds store — compound key
      if (!db.objectStoreNames.contains('rounds')) {
        const rounds = db.createObjectStore('rounds', {
          keyPath: ['game_id', 'round_num'],
        });
        rounds.createIndex('game_id', 'game_id', { unique: false });
      }
    };

    req.onsuccess = (event) => {
      _db = event.target.result;
      resolve(_db);
    };

    req.onerror = () => reject(req.error);
  });
}

/**
 * Run a single IDB request and wrap it in a Promise.
 * @param {IDBRequest} req
 * @returns {Promise<any>}
 */
function _wrap(req) {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

// ─── public API ──────────────────────────────────────────────────────────────

/**
 * Open the database. Resolves when the DB is ready.
 * @returns {Promise<void>}
 */
export async function openGameStore() {
  await _open();
}

/**
 * Persist a game object (insert or overwrite).
 * @param {Object} game
 * @returns {Promise<void>}
 */
export async function saveGame(game) {
  const db = await _open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('games', 'readwrite');
    const req = tx.objectStore('games').put(game);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
    tx.onerror = () => reject(tx.error);
  });
}

/**
 * Retrieve a game by id, or null if not found.
 * @param {number|string} id
 * @returns {Promise<Object|null>}
 */
export async function getGame(id) {
  const db = await _open();
  const tx = db.transaction('games', 'readonly');
  const result = await _wrap(tx.objectStore('games').get(_normalizeId(id)));
  return result ?? null;
}

/**
 * Return the first game with status="active", or null.
 * @returns {Promise<Object|null>}
 */
export async function getActiveGame() {
  const db = await _open();
  const tx = db.transaction('games', 'readonly');
  const index = tx.objectStore('games').index('status');
  const result = await _wrap(index.get('active'));
  return result ?? null;
}

/**
 * Persist a round (insert or overwrite).
 * @param {Object} round  Must contain game_id and round_num.
 * @returns {Promise<void>}
 */
export async function saveRound(round) {
  const db = await _open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('rounds', 'readwrite');
    const req = tx.objectStore('rounds').put(round);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
    tx.onerror = () => reject(tx.error);
  });
}

/**
 * Retrieve a round by (gameId, roundNum), or null if not found.
 * @param {number} gameId
 * @param {number} roundNum
 * @returns {Promise<Object|null>}
 */
export async function getRound(gameId, roundNum) {
  const db = await _open();
  const tx = db.transaction('rounds', 'readonly');
  const result = await _wrap(tx.objectStore('rounds').get([_normalizeId(gameId), roundNum]));
  return result ?? null;
}

/**
 * Return all rounds for a game, sorted ascending by round_num.
 * @param {number} gameId
 * @returns {Promise<Object[]>}
 */
export async function getRoundsForGame(gameId) {
  const db = await _open();
  const tx = db.transaction('rounds', 'readonly');
  const index = tx.objectStore('rounds').index('game_id');
  const results = await _wrap(index.getAll(_normalizeId(gameId)));
  return (results ?? []).sort((a, b) => a.round_num - b.round_num);
}

/**
 * Delete a specific round.
 * @param {number} gameId
 * @param {number} roundNum
 * @returns {Promise<void>}
 */
export async function deleteRound(gameId, roundNum) {
  const db = await _open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('rounds', 'readwrite');
    const req = tx.objectStore('rounds').delete([_normalizeId(gameId), roundNum]);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
    tx.onerror = () => reject(tx.error);
  });
}

/**
 * Return finished games, most-recently-started first, up to `limit`.
 * @param {number} [limit=20]
 * @returns {Promise<Object[]>}
 */
export async function getFinishedGames(limit = 20) {
  const db = await _open();
  const tx = db.transaction('games', 'readonly');
  const index = tx.objectStore('games').index('status');
  const all = await _wrap(index.getAll('finished'));
  // Sort by started_at descending (most recent first), then slice.
  return (all ?? [])
    .sort((a, b) => {
      if (a.started_at > b.started_at) return -1;
      if (a.started_at < b.started_at) return 1;
      return 0;
    })
    .slice(0, limit);
}

// ─── test helpers (no-op in production) ──────────────────────────────────────

/**
 * Close and null the cached connection so the next call to _open() starts fresh.
 * Only used by tests via beforeEach.
 */
export function resetForTesting() {
  if (_db) {
    _db.close();
    _db = null;
  }
}

/**
 * Replace the global indexedDB factory. Used in tests to swap in a fresh
 * fake-indexeddb IDBFactory instance so each test has an empty database.
 * @param {IDBFactory} factory
 */
export function setIndexedDBForTesting(factory) {
  globalThis.indexedDB = factory;
}
