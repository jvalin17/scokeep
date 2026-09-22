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
const DB_VERSION = 2;

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
      const oldVersion = event.oldVersion;

      // v1: games + rounds stores
      if (oldVersion < 1) {
        const games = db.createObjectStore('games', { keyPath: 'id' });
        games.createIndex('status', 'status', { unique: false });
        games.createIndex('playground_id', 'playground_id', { unique: false });

        const rounds = db.createObjectStore('rounds', {
          keyPath: ['game_id', 'round_num'],
        });
        rounds.createIndex('game_id', 'game_id', { unique: false });
      }

      // v2: rooms store for offline Quick Game
      if (oldVersion < 2) {
        db.createObjectStore('rooms', { keyPath: 'share_code' });
      }
    };

    req.onsuccess = (event) => {
      _db = event.target.result;
      _db.onversionchange = () => { _db.close(); _db = null; };
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

/**
 * Run a readwrite put on the named store.
 * @param {string} storeName
 * @param {any} value
 * @returns {Promise<void>}
 */
async function _put(storeName, value) {
  const db = await _open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readwrite');
    const req = tx.objectStore(storeName).put(value);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
    tx.onerror = () => reject(tx.error);
  });
}

/**
 * Run a readwrite delete on the named store.
 * @param {string} storeName
 * @param {any} key
 * @returns {Promise<void>}
 */
async function _del(storeName, key) {
  const db = await _open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readwrite');
    const req = tx.objectStore(storeName).delete(key);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
    tx.onerror = () => reject(tx.error);
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
export function saveGame(game) {
  return _put('games', game);
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
export function saveRound(round) {
  return _put('rounds', round);
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
export function deleteRound(gameId, roundNum) {
  return _del('rounds', [_normalizeId(gameId), roundNum]);
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

/**
 * Atomically save a game and a round in a single IDB transaction.
 * Prevents ghost games if the browser crashes between writes.
 * @param {Object} game
 * @param {Object} round  Must contain game_id and round_num.
 * @returns {Promise<void>}
 */
export async function saveGameAndRound(game, round) {
  const db = await _open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(['games', 'rounds'], 'readwrite');
    tx.objectStore('games').put(game);
    tx.objectStore('rounds').put(round);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error || new Error('Transaction aborted'));
  });
}

/**
 * Return all games with sync_pending=true.
 * @returns {Promise<Object[]>}
 */
export async function getSyncPendingGames() {
  const db = await _open();
  const tx = db.transaction('games', 'readonly');
  const all = await _wrap(tx.objectStore('games').getAll());
  return (all ?? []).filter(g => g.sync_pending === true);
}

// ─── rooms store (v2) ────────────────────────────────────────────────────────

/**
 * Persist a room object (insert or overwrite).
 * @param {Object} room — must have share_code as keyPath
 * @returns {Promise<void>}
 */
export function saveRoom(room) {
  return _put('rooms', room);
}

/**
 * Retrieve a room by share_code.
 * @param {string} shareCode
 * @returns {Promise<Object|null>}
 */
export async function getRoom(shareCode) {
  const db = await _open();
  const tx = db.transaction('rooms', 'readonly');
  const result = await _wrap(tx.objectStore('rooms').get(shareCode));
  return result ?? null;
}

/**
 * Return all cached rooms.
 * @returns {Promise<Object[]>}
 */
export async function getAllRooms() {
  const db = await _open();
  const tx = db.transaction('rooms', 'readonly');
  const results = await _wrap(tx.objectStore('rooms').getAll());
  return results ?? [];
}

/**
 * Delete a room by share_code.
 * @param {string} shareCode
 * @returns {Promise<void>}
 */
export function deleteRoom(shareCode) {
  return _del('rooms', shareCode);
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
