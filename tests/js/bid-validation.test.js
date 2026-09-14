/**
 * bid-validation.test.js
 *
 * Tests for validateBid() ported from Python RoundService.submit_bid must-lose logic.
 * Drives implementation of app/static/js/engine/bid.js.
 *
 * Run with: npx vitest run tests/js/bid-validation.test.js
 */

import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { describe, it, expect } from 'vitest';

import { validateBid } from '../../app/static/js/engine/bid.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const vectors = JSON.parse(
    readFileSync(join(__dirname, '../vectors/bid_vectors.json'), 'utf8')
);

// ─── Vector-driven tests ──────────────────────────────────────────────────────

describe('bid-validation — vector-driven tests', () => {
    for (const vec of vectors) {
        it(`[${vec.id}] ${vec.description}`, () => {
            const result = validateBid(
                vec.existingBids,
                vec.playerIndex,
                vec.value,
                {
                    mustLose: vec.mustLose,
                    cardsDeal: vec.cardsDeal,
                    playerCount: vec.playerCount,
                }
            );

            if (vec.expectError) {
                expect(result).not.toBeNull();
                expect(typeof result).toBe('string');
            } else {
                expect(result).toBeNull();
            }
        });
    }
});

// ─── Explicit named tests (mirror Python class structure) ─────────────────────

describe('bid-validation — explicit named tests', () => {
    it('must-lose: last player rejected when total equals cards_dealt', () => {
        const result = validateBid(
            { '0': 2, '1': 3 },
            2,
            3,
            { mustLose: true, cardsDeal: 8, playerCount: 3 }
        );
        expect(result).not.toBeNull();
        expect(typeof result).toBe('string');
    });

    it('must-lose: last player allowed when total differs from cards_dealt', () => {
        const result = validateBid(
            { '0': 2, '1': 3 },
            2,
            2,
            { mustLose: true, cardsDeal: 8, playerCount: 3 }
        );
        expect(result).toBeNull();
    });

    it('must-lose: non-last player always allowed regardless of total', () => {
        const result = validateBid(
            { '0': 4 },
            1,
            4,
            { mustLose: true, cardsDeal: 8, playerCount: 3 }
        );
        expect(result).toBeNull();
    });

    it('must-lose disabled: last player can cause total to equal cards_dealt', () => {
        const result = validateBid(
            { '0': 2, '1': 3 },
            2,
            3,
            { mustLose: false, cardsDeal: 8, playerCount: 3 }
        );
        expect(result).toBeNull();
    });

    it('1-card edge case: last player bid=1 rejected (0+0+1 == 1)', () => {
        const result = validateBid(
            { '0': 0, '1': 0 },
            2,
            1,
            { mustLose: true, cardsDeal: 1, playerCount: 3 }
        );
        expect(result).not.toBeNull();
    });

    it('1-card edge case: last player bid=0 allowed (0+0+0 != 1)', () => {
        const result = validateBid(
            { '0': 0, '1': 0 },
            2,
            0,
            { mustLose: true, cardsDeal: 1, playerCount: 3 }
        );
        expect(result).toBeNull();
    });

    it('duplicate bid: player who already bid is rejected', () => {
        const result = validateBid(
            { '0': 2, '1': 3 },
            1,
            1,
            { mustLose: false, cardsDeal: 8, playerCount: 3 }
        );
        expect(result).not.toBeNull();
    });

    it('negative bid is rejected', () => {
        const result = validateBid(
            { '0': 2 },
            1,
            -1,
            { mustLose: false, cardsDeal: 8, playerCount: 3 }
        );
        expect(result).not.toBeNull();
    });
});
