/**
 * TDD gate + How To Scoresheet coverage for screens/home.js.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const homeJs = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../../app/static/js/screens/home.js'),
  'utf8',
);

describe('home How To', () => {
  it('includes Scoresheet section with settings and entry flow', () => {
    expect(homeJs).toContain('How to Use Scoresheet');
    for (const needle of [
      'Show totals',
      'Allow negatives',
      'Highest',
      'Lowest',
      'dialer',
      'Next Round',
      'Finished',
      'Undo Last Round',
    ]) {
      expect(homeJs, `missing: ${needle}`).toContain(needle);
    }
  });
});
