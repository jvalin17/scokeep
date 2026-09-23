/**
 * Tests for resolve-api.js — all gameplay goes through game-api.js (IDB-first).
 */
import { describe, it, expect } from 'vitest';
import { isLocalGame, getApi } from '../../app/static/js/resolve-api.js';

describe('isLocalGame', () => {
  it('returns true for string IDs starting with "game-"', () => {
    expect(isLocalGame('game-1726300000-abc1234')).toBe(true);
    expect(isLocalGame('game-foo')).toBe(true);
  });

  it('returns false for integer IDs (server games)', () => {
    expect(isLocalGame(42)).toBe(false);
    expect(isLocalGame(1)).toBe(false);
  });

  it('returns false for numeric string IDs (server games passed as strings)', () => {
    expect(isLocalGame('42')).toBe(false);
    expect(isLocalGame('1')).toBe(false);
  });

  it('returns false for null/undefined', () => {
    expect(isLocalGame(null)).toBe(false);
    expect(isLocalGame(undefined)).toBe(false);
  });
});

describe('getApi', () => {
  it('returns game-api module for local game IDs', async () => {
    const api = await getApi('game-1726300000-abc1234');
    expect(api).toHaveProperty('createGame');
    expect(api).toHaveProperty('submitBid');
    expect(api).toHaveProperty('loadGameFromServer');
  });

  it('returns game-api module for server game IDs', async () => {
    const api = await getApi(42);
    expect(api).toHaveProperty('createGame');
    expect(api).toHaveProperty('submitBid');
    expect(api).toHaveProperty('loadGameFromServer');
    expect(api).toHaveProperty('createOnlineGame');
  });

  it('returns game-api module for numeric string IDs', async () => {
    const api = await getApi('7');
    expect(api).toHaveProperty('createGame');
    expect(api).toHaveProperty('loadGameFromServer');
  });
});
