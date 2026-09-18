/**
 * pin-verifier.js — Offline PIN verification using PBKDF2.
 *
 * Uses Web Crypto API (built-in, no external dependencies).
 * PIN is never stored — only a PBKDF2-derived verifier (salt + hash).
 *
 * Rate limiter prevents brute-force: 5 free attempts, then exponential
 * lockout (1, 2, 4, 8, 16, 32, 60 min).
 *
 * Reference: requirements/quick-game-sync.md, architecture/quick-game-sync.md
 */

const ITERATIONS = 600000;
const HASH_ALGORITHM = 'SHA-256';
const SALT_BYTES = 16;
const KEY_BITS = 256;
const MAX_FREE_ATTEMPTS = 5;
const MAX_LOCKOUT_MINUTES = 60;

/**
 * Convert a byte array to a hex string.
 * @param {Uint8Array} bytes
 * @returns {string}
 */
function bytesToHex(bytes) {
  return Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
}

/**
 * Convert a hex string to a byte array.
 * @param {string} hex
 * @returns {Uint8Array}
 */
function hexToBytes(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.substring(i, i + 2), 16);
  }
  return bytes;
}

/**
 * Derive a PBKDF2 hash from a PIN and salt.
 * @param {string} pin — the raw PIN string
 * @param {Uint8Array} salt — 16-byte salt
 * @returns {Promise<string>} hex-encoded derived key
 */
async function deriveKey(pin, salt) {
  const encoder = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    'raw', encoder.encode(pin), 'PBKDF2', false, ['deriveBits']
  );
  const derivedBits = await crypto.subtle.deriveBits(
    { name: 'PBKDF2', salt, iterations: ITERATIONS, hash: HASH_ALGORITHM },
    keyMaterial,
    KEY_BITS
  );
  return bytesToHex(new Uint8Array(derivedBits));
}

/**
 * Create a PIN verifier for offline storage.
 * Called client-side after successful online auth.
 *
 * @param {string} pin — the raw PIN (e.g. "1234")
 * @returns {Promise<{salt: string, hash: string, iterations: number}>}
 */
export async function createVerifier(pin) {
  const salt = crypto.getRandomValues(new Uint8Array(SALT_BYTES));
  const hash = await deriveKey(pin, salt);
  return { salt: bytesToHex(salt), hash, iterations: ITERATIONS };
}

/**
 * Check a PIN against a stored verifier.
 *
 * @param {string} pin — the PIN to check
 * @param {{salt: string, hash: string, iterations: number}} verifier
 * @returns {Promise<boolean>}
 */
export async function checkPin(pin, verifier) {
  const derivedHash = await deriveKey(pin, hexToBytes(verifier.salt));
  return constantTimeEqual(derivedHash, verifier.hash);
}

/**
 * Constant-time string comparison to prevent timing side-channel attacks.
 * @param {string} stringA
 * @param {string} stringB
 * @returns {boolean}
 */
function constantTimeEqual(stringA, stringB) {
  if (stringA.length !== stringB.length) return false;
  let mismatch = 0;
  for (let i = 0; i < stringA.length; i++) {
    mismatch |= stringA.charCodeAt(i) ^ stringB.charCodeAt(i);
  }
  return mismatch === 0;
}

/**
 * Check if a room is currently locked out.
 *
 * @param {{attempts: number, locked_until: number|null}} roomState
 * @returns {boolean}
 */
export function isLocked(roomState) {
  if (!roomState.locked_until) return false;
  const lockExpiry = typeof roomState.locked_until === 'number'
    ? roomState.locked_until
    : new Date(roomState.locked_until).getTime();
  return Date.now() < lockExpiry;
}

/**
 * Record a PIN attempt and enforce rate limiting.
 * Mutates roomState in place (caller persists to IndexedDB).
 *
 * @param {{attempts: number, locked_until: number|null}} roomState
 * @param {boolean} success — whether the PIN was correct
 * @returns {{allowed: boolean, locked_until: number|null}}
 */
export function checkAttempt(roomState, success) {
  if (isLocked(roomState)) {
    return { allowed: false, locked_until: roomState.locked_until };
  }

  if (success) {
    roomState.attempts = 0;
    roomState.locked_until = null;
    return { allowed: true, locked_until: null };
  }

  roomState.attempts += 1;

  if (roomState.attempts > MAX_FREE_ATTEMPTS) {
    const lockoutMinutes = Math.min(
      Math.pow(2, roomState.attempts - MAX_FREE_ATTEMPTS - 1),
      MAX_LOCKOUT_MINUTES
    );
    roomState.locked_until = Date.now() + lockoutMinutes * 60000;
    return { allowed: false, locked_until: roomState.locked_until };
  }

  return { allowed: true, locked_until: null };
}

/**
 * Reset attempt counter (e.g. after successful online re-auth).
 *
 * @param {{attempts: number, locked_until: number|null}} roomState
 */
export function resetAttempts(roomState) {
  roomState.attempts = 0;
  roomState.locked_until = null;
}
