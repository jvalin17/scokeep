import { describe, it, expect, beforeAll } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

describe('global off-white teal palette', () => {
    let css;
    let manifest;

    beforeAll(() => {
        css = readFileSync(resolve('app/static/css/style.css'), 'utf8');
        manifest = JSON.parse(readFileSync(resolve('app/static/manifest.json'), 'utf8'));
    });

    it('sets root page background to off-white and accent to dark aqua', () => {
        const rootBlock = css.match(/:root\s*\{[\s\S]*?\}/)?.[0] || '';
        expect(rootBlock).toMatch(/--bg-page:\s*#F7F4EF/i);
        expect(rootBlock).toMatch(/--accent:\s*#0A5F6E/i);
        expect(rootBlock).toMatch(/--text-primary:\s*#0A3F4A/i);
        expect(rootBlock).not.toMatch(/--accent:\s*#1E3A5F/i);
        expect(rootBlock).not.toMatch(/--accent:\s*#333333/i);
    });

    it('colors the Scokeep logo with the accent (not black)', () => {
        expect(css).toMatch(/\.logo\s*\{[^}]*color:\s*var\(--accent\)/s);
    });

    it('keeps dialer ± in a 3-column bottom row (not full-width)', () => {
        expect(css).not.toMatch(/\.score-dialer-keypad\s+#btn-sign\s*\{[^}]*grid-column:\s*1\s*\/\s*-1/s);
    });

    it('keeps lobby game tabs borderless (no track chrome)', () => {
        const block = css.match(/\.lobby-game-tabs\.stats-tabs\s*\{[\s\S]*?\}/)?.[0]
            || css.match(/\.lobby-game-tabs\s*\{[\s\S]*?\}/)?.[0]
            || '';
        expect(block).toMatch(/border:\s*none/i);
        expect(block).toMatch(/background:\s*transparent/i);
        expect(block).not.toMatch(/background:\s*var\(--border-light\)/);
        expect(block).not.toMatch(/padding:\s*3px/);
    });

    it('provides focus-visible styles for tabs and keypad keys', () => {
        expect(css).toMatch(/\.stats-tab:focus-visible/);
        expect(css).toMatch(/\.keypad-key:focus-visible/);
        expect(css).toMatch(/\.stats-tab\s*\{[\s\S]*?font-size:\s*0\.875rem/s);
    });

    it('aligns PWA manifest theme with teal off-white', () => {
        expect(manifest.background_color.toUpperCase()).toBe('#F7F4EF');
        expect(manifest.theme_color.toUpperCase()).toBe('#0A5F6E');
    });
});
