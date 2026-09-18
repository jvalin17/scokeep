/**
 * Tests for pin-verifier.js — PBKDF2-based offline PIN verification.
 *
 * Uses Web Crypto API (built-in). No external dependencies.
 * Rate limiter prevents brute-force: 5 free attempts, then exponential lockout.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import {
  createVerifier,
  checkPin,
  checkAttempt,
  isLocked,
  resetAttempts,
} from '../../app/static/js/engine/pin-verifier.js';

describe('createVerifier', () => {
  it('test_create_verifier_returns_salt_hash_iterations', async () => {
    const verifier = await createVerifier('1234');
    expect(verifier).toHaveProperty('salt');
    expect(verifier).toHaveProperty('hash');
    expect(verifier).toHaveProperty('iterations');
    expect(verifier.iterations).toBe(600000);
    expect(verifier.salt).toMatch(/^[0-9a-f]{32}$/);
    expect(verifier.hash).toMatch(/^[0-9a-f]{64}$/);
  });

  it('test_create_verifier_unique_salt', async () => {
    const verifierOne = await createVerifier('1234');
    const verifierTwo = await createVerifier('1234');
    expect(verifierOne.salt).not.toBe(verifierTwo.salt);
    // Different salt → different hash even for same PIN
    expect(verifierOne.hash).not.toBe(verifierTwo.hash);
  });
});

describe('checkPin', () => {
  it('test_check_pin_correct', async () => {
    const verifier = await createVerifier('5678');
    const result = await checkPin('5678', verifier);
    expect(result).toBe(true);
  });

  it('test_check_pin_wrong', async () => {
    const verifier = await createVerifier('5678');
    const result = await checkPin('0000', verifier);
    expect(result).toBe(false);
  });
});

describe('checkAttempt (rate limiter)', () => {
  let roomState;

  beforeEach(() => {
    roomState = { attempts: 0, locked_until: null };
  });

  it('test_check_attempt_allows_five', () => {
    for (let attempt = 0; attempt < 5; attempt++) {
      const result = checkAttempt(roomState, false);
      expect(result.allowed).toBe(true);
    }
  });

  it('test_check_attempt_locks_after_five', () => {
    // Simulate 5 failed attempts
    for (let attempt = 0; attempt < 5; attempt++) {
      checkAttempt(roomState, false);
    }
    // 6th attempt should be locked
    const result = checkAttempt(roomState, false);
    expect(result.allowed).toBe(false);
    expect(result.locked_until).toBeGreaterThan(Date.now());
  });

  it('test_check_attempt_resets_on_success', () => {
    // Simulate 4 failed attempts
    for (let attempt = 0; attempt < 4; attempt++) {
      checkAttempt(roomState, false);
    }
    expect(roomState.attempts).toBe(4);

    // Successful attempt resets counter
    const result = checkAttempt(roomState, true);
    expect(result.allowed).toBe(true);
    expect(roomState.attempts).toBe(0);
    expect(roomState.locked_until).toBeNull();
  });
});

describe('isLocked', () => {
  it('test_is_locked_expired', () => {
    const roomState = {
      attempts: 6,
      locked_until: Date.now() - 1000, // 1 second ago — expired
    };
    expect(isLocked(roomState)).toBe(false);
  });

  it('test_is_locked_active', () => {
    const roomState = {
      attempts: 6,
      locked_until: Date.now() + 60000, // 1 minute from now
    };
    expect(isLocked(roomState)).toBe(true);
  });

  it('test_is_locked_no_lockout', () => {
    const roomState = { attempts: 0, locked_until: null };
    expect(isLocked(roomState)).toBe(false);
  });
});

describe('resetAttempts', () => {
  it('test_reset_attempts', () => {
    const roomState = { attempts: 7, locked_until: Date.now() + 60000 };
    resetAttempts(roomState);
    expect(roomState.attempts).toBe(0);
    expect(roomState.locked_until).toBeNull();
  });
});

describe('checkPin edge cases', () => {
  it('test_check_pin_empty_string', async () => {
    const verifier = await createVerifier('1234');
    const result = await checkPin('', verifier);
    expect(result).toBe(false);
  });
});

describe('checkAttempt lockout duration sequence', () => {
  it('test_lockout_duration_doubles_then_caps_at_60', () => {
    const roomState = { attempts: 0, locked_until: null };
    const now = Date.now();

    // Burn through 5 free attempts
    for (let i = 0; i < 5; i++) {
      const result = checkAttempt(roomState, false);
      expect(result.allowed).toBe(true);
    }
    expect(roomState.attempts).toBe(5);

    // Attempt 6 → locked for 1 min (2^0 = 1)
    let result = checkAttempt(roomState, false);
    expect(result.allowed).toBe(false);
    expect(result.locked_until).toBeGreaterThan(now);
    const lockout1 = result.locked_until - now;
    expect(lockout1).toBeGreaterThanOrEqual(59000); // ~1 min
    expect(lockout1).toBeLessThanOrEqual(61000);

    // Expire the lock to allow next attempt
    roomState.locked_until = now - 1;

    // Attempt 7 → locked for 2 min (2^1 = 2)
    result = checkAttempt(roomState, false);
    expect(result.allowed).toBe(false);
    const lockout2 = result.locked_until - Date.now();
    expect(lockout2).toBeGreaterThanOrEqual(110000); // ~2 min
    expect(lockout2).toBeLessThanOrEqual(130000);

    roomState.locked_until = now - 1;

    // Attempt 8 → locked for 4 min (2^2 = 4)
    result = checkAttempt(roomState, false);
    expect(result.allowed).toBe(false);
    const lockout3 = result.locked_until - Date.now();
    expect(lockout3).toBeGreaterThanOrEqual(230000); // ~4 min
    expect(lockout3).toBeLessThanOrEqual(250000);
  });

  it('test_check_attempt_while_locked_returns_not_allowed', () => {
    const roomState = {
      attempts: 7,
      locked_until: Date.now() + 60000, // actively locked
    };
    const result = checkAttempt(roomState, false);
    expect(result.allowed).toBe(false);
    // Attempts should NOT increment while locked
    expect(roomState.attempts).toBe(7);
  });
});
