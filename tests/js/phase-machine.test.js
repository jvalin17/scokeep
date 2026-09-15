/**
 * Phase state machine tests — parity with Python GameService.advance_round / extend_game.
 * Vectors loaded from tests/vectors/phase_vectors.json.
 *
 * Run with: npx vitest run tests/js/phase-machine.test.js
 */

import { readFileSync } from 'fs';
import { describe, it, expect } from 'vitest';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

import { advanceRound, extendGame } from '../../app/static/js/engine/phase.js';

const __filename = fileURLToPath(import.meta.url);
const __dir = dirname(__filename);

const vectors = JSON.parse(
    readFileSync(join(__dir, '../vectors/phase_vectors.json'), 'utf8')
);

// ---------------------------------------------------------------------------
// advanceRound
// ---------------------------------------------------------------------------

describe('advanceRound — vector cases', () => {
    for (const vec of vectors.advance_round) {
        it(`${vec.id}: ${vec.description}`, () => {
            const input = structuredClone(vec.input);
            const result = advanceRound(input);

            // Result must match expected fields
            expect(result.current_round).toBe(vec.expected.current_round);
            expect(result.total_rounds).toBe(vec.expected.total_rounds);
            expect(result.dealer_index).toBe(vec.expected.dealer_index);
            expect(result.phase).toBe(vec.expected.phase);
            expect(result.players).toEqual(vec.expected.players);
        });
    }
});

describe('advanceRound — purity', () => {
    it('does not mutate the input game object', () => {
        const input = {
            current_round: 3,
            total_rounds: 8,
            dealer_index: 1,
            players: ['Alice', 'Bob', 'Carol'],
            phase: 'scoreboard',
        };
        const snapshot = JSON.stringify(input);
        advanceRound(input);
        expect(JSON.stringify(input)).toBe(snapshot);
    });

    it('returns a new object, not the same reference', () => {
        const input = {
            current_round: 3,
            total_rounds: 8,
            dealer_index: 1,
            players: ['Alice', 'Bob', 'Carol'],
            phase: 'scoreboard',
        };
        const result = advanceRound(input);
        expect(result).not.toBe(input);
    });
});

// ---------------------------------------------------------------------------
// extendGame
// ---------------------------------------------------------------------------

describe('extendGame — vector cases', () => {
    for (const vec of vectors.extend_game) {
        it(`${vec.id}: ${vec.description}`, () => {
            const input = structuredClone(vec.input);
            const result = extendGame(input);

            expect(result.total_rounds).toBe(vec.expected.total_rounds);
            expect(result.settings.num_sets).toBe(vec.expected.settings.num_sets);
            // current_round, dealer_index, players, phase unchanged
            expect(result.current_round).toBe(vec.expected.current_round);
            expect(result.dealer_index).toBe(vec.expected.dealer_index);
            expect(result.phase).toBe(vec.expected.phase);
            expect(result.players).toEqual(vec.expected.players);

            // settings object preserved (if rounds_per_set was present, it stays)
            if ('rounds_per_set' in vec.input.settings) {
                expect(result.settings.rounds_per_set).toBe(vec.input.settings.rounds_per_set);
            }
        });
    }
});

describe('extendGame — purity', () => {
    it('does not mutate the input game object', () => {
        const input = {
            current_round: 8,
            total_rounds: 24,
            dealer_index: 0,
            players: ['Alice', 'Bob'],
            phase: 'review',
            settings: { rounds_per_set: 8, num_sets: 3 },
        };
        const snapshot = JSON.stringify(input);
        extendGame(input);
        expect(JSON.stringify(input)).toBe(snapshot);
    });

    it('does not mutate the nested settings object', () => {
        const settings = { rounds_per_set: 8, num_sets: 3 };
        const input = {
            current_round: 8,
            total_rounds: 24,
            dealer_index: 0,
            players: ['Alice', 'Bob'],
            phase: 'review',
            settings,
        };
        extendGame(input);
        expect(settings.num_sets).toBe(3);
    });

    it('returns a new object, not the same reference', () => {
        const input = {
            current_round: 8,
            total_rounds: 24,
            dealer_index: 0,
            players: ['Alice', 'Bob'],
            phase: 'review',
            settings: { rounds_per_set: 8, num_sets: 3 },
        };
        const result = extendGame(input);
        expect(result).not.toBe(input);
        expect(result.settings).not.toBe(input.settings);
    });
});
