/**
 * Co-located next to sw.js for TDD gate discovery (hook cwd may not be repo root).
 * Run: npx vitest run app/static/sw.test.js
 */
import { readFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import { describe, expect, it } from 'vitest';

const __dirname = dirname(fileURLToPath(import.meta.url));
const swSource = readFileSync(join(__dirname, 'sw.js'), 'utf8');

describe('service worker fetch handler', () => {
  it('does not respondWith for /api/ requests', () => {
    const apiMarker = "pathname.startsWith('/api/')";
    expect(swSource).toContain(apiMarker);
    const apiStart = swSource.indexOf(apiMarker);
    const appShellMarker = '// App shell:';
    const apiBlock = swSource.slice(apiStart, swSource.indexOf(appShellMarker, apiStart));
    expect(apiBlock).not.toContain('respondWith');
    expect(apiBlock).toContain('return;');
    expect(swSource).not.toContain('You are offline');
  });
});
