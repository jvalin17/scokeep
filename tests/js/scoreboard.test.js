/**
 * scoreboard.test.js
 *
 * Tests for computeScoreboard() ported from Python ScoreboardService.get_scoreboard.
 * Drives implementation of app/static/js/engine/scoreboard.js.
 *
 * Run with: npx vitest run tests/js/scoreboard.test.js
 */

import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { describe, it, expect } from 'vitest';

import { computeScoreboard } from '../../app/static/js/engine/scoreboard.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const vectors = JSON.parse(
    readFileSync(join(__dirname, '../vectors/scoreboard_vectors.json'), 'utf8')
);

// ─── Vector-driven tests ──────────────────────────────────────────────────────

describe('scoreboard — vector-driven tests', () => {
    for (const vec of vectors) {
        it(`[${vec.id}] ${vec.description} — totals`, () => {
            const result = computeScoreboard(vec.rounds, vec.player_count);
            expect(result.totals).toEqual(vec.expected_totals);
        });

        it(`[${vec.id}] ${vec.description} — rounds array length`, () => {
            const result = computeScoreboard(vec.rounds, vec.player_count);
            expect(Array.isArray(result.rounds)).toBe(true);
            expect(result.rounds.length).toBe(vec.rounds.length);
        });
    }
});

// ─── Explicit named tests (mirror Python class structure) ─────────────────────

describe('scoreboard — explicit named tests', () => {
    it('returns object with totals and rounds keys', () => {
        const result = computeScoreboard([], 0);
        expect(result.totals).toBeDefined();
        expect(result.rounds).toBeDefined();
    });

    it('empty rounds with player_count=2 gives zero totals for both players', () => {
        const result = computeScoreboard([], 2);
        expect(result.totals).toEqual({ '0': 0, '1': 0 });
    });

    it('single round scores become totals', () => {
        const rounds = [
            {
                round_num: 1,
                cards_dealt: 8,
                trump_suit: 'hearts',
                bids: { '0': 2, '1': 3 },
                hands_won: { '0': 2, '1': 3 },
                scores: { '0': 20, '1': 30 },
            },
        ];
        const result = computeScoreboard(rounds, 2);
        expect(result.totals['0']).toBe(20);
        expect(result.totals['1']).toBe(30);
    });

    it('two rounds accumulate scores for each player', () => {
        const rounds = [
            {
                round_num: 1,
                cards_dealt: 8,
                trump_suit: 'clubs',
                bids: { '0': 2 },
                hands_won: { '0': 2 },
                scores: { '0': 20 },
            },
            {
                round_num: 2,
                cards_dealt: 7,
                trump_suit: 'diamonds',
                bids: { '0': 1 },
                hands_won: { '0': 3 },
                scores: { '0': -10 },
            },
        ];
        const result = computeScoreboard(rounds, 1);
        expect(result.totals['0']).toBe(10);
    });

    it('player_count fills missing players with 0', () => {
        const rounds = [
            {
                round_num: 1,
                cards_dealt: 4,
                trump_suit: 'spades',
                bids: { '0': 1 },
                hands_won: { '0': 1 },
                scores: { '0': 11 },
            },
        ];
        const result = computeScoreboard(rounds, 3);
        expect(result.totals['1']).toBe(0);
        expect(result.totals['2']).toBe(0);
    });

    it('player already in scores is not overwritten by player_count fill', () => {
        const rounds = [
            {
                round_num: 1,
                cards_dealt: 4,
                trump_suit: 'hearts',
                bids: { '0': 2, '1': 1 },
                hands_won: { '0': 2, '1': 1 },
                scores: { '0': 20, '1': 11 },
            },
        ];
        const result = computeScoreboard(rounds, 2);
        expect(result.totals['0']).toBe(20);
        expect(result.totals['1']).toBe(11);
    });

    it('rounds data passthrough preserves all fields', () => {
        const rounds = [
            {
                round_num: 3,
                cards_dealt: 5,
                trump_suit: 'diamonds',
                bids: { '0': 2 },
                hands_won: { '0': 2 },
                scores: { '0': 20 },
            },
        ];
        const result = computeScoreboard(rounds, 1);
        expect(result.rounds[0].round_num).toBe(3);
        expect(result.rounds[0].cards_dealt).toBe(5);
        expect(result.rounds[0].trump_suit).toBe('diamonds');
        expect(result.rounds[0].scores).toEqual({ '0': 20 });
    });

    it('negative cumulative total when player misses bids', () => {
        const rounds = [
            {
                round_num: 1,
                cards_dealt: 5,
                trump_suit: 'clubs',
                bids: { '0': 3 },
                hands_won: { '0': 1 },
                scores: { '0': -30 },
            },
            {
                round_num: 2,
                cards_dealt: 4,
                trump_suit: 'hearts',
                bids: { '0': 2 },
                hands_won: { '0': 4 },
                scores: { '0': -20 },
            },
        ];
        const result = computeScoreboard(rounds, 1);
        expect(result.totals['0']).toBe(-50);
    });

    it('pure function — does not mutate input rounds array', () => {
        const rounds = [
            {
                round_num: 1,
                cards_dealt: 4,
                trump_suit: 'spades',
                bids: { '0': 1 },
                hands_won: { '0': 1 },
                scores: { '0': 11 },
            },
        ];
        const originalLength = rounds.length;
        computeScoreboard(rounds, 1);
        expect(rounds.length).toBe(originalLength);
    });
});
