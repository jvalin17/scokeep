/**
 * lobby-cleanup.test.js — L7: Verify lobby clears setTimeout on unmount.
 *
 * Structural test: verifies source code captures and clears the sync timer.
 *
 * Run with: npx vitest run tests/js/lobby-cleanup.test.js --environment node
 */

import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

// @vitest-environment node

describe('test_lobby_sync_timer_cleared_on_unmount', () => {
  it('lobby.js captures setTimeout and clears it in unmount', () => {
    const source = readFileSync(
      resolve(process.cwd(), 'app/static/js/screens/lobby.js'),
      'utf-8'
    );

    // After L7 fix: setTimeout return value is captured in syncTimer
    expect(source).toMatch(/syncTimer\s*=\s*setTimeout/);

    // After L7 fix: unmount calls clearTimeout(syncTimer)
    expect(source).toMatch(/clearTimeout\(syncTimer\)/);
  });
});
