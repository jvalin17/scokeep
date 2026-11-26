import { describe, it, expect, beforeAll } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { getTrump, suitColorClass } from '../../app/static/js/components/game-utils.js';
import { renderTrumpDisplay, renderScoresheetTable } from '../../app/static/js/components/screen-parts.js';
import { renderPersonalityCards } from '../../app/static/js/components/personality-card.js';
import { renderGameDetail } from '../../app/static/js/components/stats-charts.js';

describe('suitColorClass', () => {
    it('marks spades and clubs black', () => {
        expect(suitColorClass('♠')).toBe('trump-black');
        expect(suitColorClass('♣')).toBe('trump-black');
    });

    it('marks diamonds and hearts red', () => {
        expect(suitColorClass('♦')).toBe('trump-red');
        expect(suitColorClass('♥')).toBe('trump-red');
    });
});

describe('getTrump colorClass', () => {
    it('gives black suits a trump-black class instead of no class', () => {
        expect(getTrump(1).colorClass).toBe('trump-black'); // spades
        expect(getTrump(3).colorClass).toBe('trump-black'); // clubs
    });

    it('keeps red suits on trump-red', () => {
        expect(getTrump(2).colorClass).toBe('trump-red'); // diamonds
        expect(getTrump(4).colorClass).toBe('trump-red'); // hearts
    });
});

describe('trump-black CSS rule', () => {
    let css;

    beforeAll(() => {
        css = readFileSync(resolve('app/static/css/style.css'), 'utf8');
    });

    it('colors the black-suit symbol and name black, mirroring trump-red', () => {
        const blackRule = css.match(/\.trump-black[^{]*\{[^}]*\}/)?.[0] || '';
        expect(blackRule).toMatch(/color:\s*#000/i);
        expect(blackRule).toMatch(/\.trump-black\s+\.trump-symbol/);
        expect(blackRule).toMatch(/\.trump-black\s+\.trump-name/);
    });

    it('leaves the red rule intact', () => {
        const redRule = css.match(/\.trump-red[^{]*\{[^}]*\}/)?.[0] || '';
        expect(redRule).toMatch(/color:\s*#D32F2F/i);
    });
});

describe('renderTrumpDisplay suit color', () => {
    it('tags the large spades display black, not bare', () => {
        const html = renderTrumpDisplay(1, 'friendly', 'large');
        expect(html).toContain('trump-display trump-black');
        expect(html).not.toContain('trump-red');
    });

    it('tags the small clubs display black', () => {
        const html = renderTrumpDisplay(3, 'rookie', 'small');
        expect(html).toContain('trump-below trump-black');
    });

    it('still tags red suits red', () => {
        expect(renderTrumpDisplay(2, 'friendly', 'large')).toContain('trump-display trump-red');
        expect(renderTrumpDisplay(4, 'rookie', 'small')).toContain('trump-below trump-red');
    });
});

describe('scoresheet table suit color', () => {
    const players = ['Alice', 'Bob'];
    const rounds = [
        { round_num: 1, cards_dealt: 8, scores: { 0: 10, 1: -5 } },
        { round_num: 2, cards_dealt: 7, scores: { 0: 5, 1: 5 } },
    ];
    const totals = { 0: 15, 1: 0 };

    it('gives the spades cell a trump-black class', () => {
        const html = renderScoresheetTable(players, rounds, totals);
        expect(html).toContain('<span class="trump-black"');
        expect(html).not.toContain('<span class=""');
    });

    it('gives the diamonds cell a trump-red class', () => {
        const html = renderScoresheetTable(players, rounds, totals);
        expect(html).toContain('<span class="trump-red"');
    });
});

describe('game detail table suit color', () => {
    it('gives the spades cell a trump-black class', () => {
        const game = { id: 1, players: ['Alice'], created_at: '2026-01-01T00:00:00Z' };
        const scoreboard = {
            players: ['Alice'],
            rounds: [{ round_num: 1, cards_dealt: 8, scores: { 0: 10 }, bids: { 0: 2 }, hands_won: { 0: 2 } }],
            totals: { 0: 10 },
        };
        const html = renderGameDetail(game, scoreboard, false);
        expect(html).toContain('class="trump-black"');
        expect(html).not.toContain('<span class=""');
    });
});

describe('personality card best suit color', () => {
    function makePlayer(extras) {
        return {
            personality: 'The Strategist',
            meta: { name: 'The Strategist', tagline: 'Plays with precision', color: '#43A047', icon: '🎯' },
            accuracy_by_cards: {},
            insights: [],
            extras,
            games_analyzed: 5,
        };
    }

    it('renders a black best suit with the trump-black class, not an uncolored span', () => {
        const html = renderPersonalityCards({
            Alice: makePlayer({ best_trump: '♠', best_trump_pct: 72 }),
        });
        expect(html).toContain('class="trump-black"');
    });

    it('renders a red best suit with the trump-red class instead of an inline color', () => {
        const html = renderPersonalityCards({
            Bob: makePlayer({ best_trump: '♥', best_trump_pct: 64 }),
        });
        expect(html).toContain('class="trump-red"');
        expect(html).not.toContain('style="color:#D32F2F;"');
    });
});
