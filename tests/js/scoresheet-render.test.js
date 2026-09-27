/**
 * scoresheet-render.test.js
 *
 * Tests that renderScoresheetTable shows cards_dealt (not round_num)
 * in the first column, so players can track the card count pattern.
 */

import { describe, it, expect, vi } from 'vitest';

// Mock modules that screen-parts.js imports but we don't need
vi.mock('../../app/static/js/components/confirm-dialog.js', () => ({
    showConfirmDialog: vi.fn(),
}));
vi.mock('../../app/static/js/resolve-api.js', () => ({
    getApi: vi.fn(),
}));

import { renderScoresheetTable } from '../../app/static/js/components/screen-parts.js';

describe('renderScoresheetTable', () => {
    it('test_scoresheet_shows_cards_dealt_not_round_num', () => {
        // Arrange — round 13 has 5 cards (set 2, ascending position 5)
        const players = ['Alice', 'Bob'];
        const rounds = [
            { round_num: 13, cards_dealt: 5, scores: { '0': 10, '1': -5 } },
        ];
        const totals = { '0': 10, '1': -5 };

        // Act
        const html = renderScoresheetTable(players, rounds, totals);

        // Assert — should contain "5" (cards_dealt) not "13" (round_num) in the row
        expect(html).toContain('>5<span');
        expect(html).not.toContain('>13<span');
    });

    it('test_scoresheet_shows_descending_then_ascending_card_pattern', () => {
        // Arrange — rounds spanning set boundary
        const players = ['Alice'];
        const rounds = [
            { round_num: 7, cards_dealt: 2, scores: { '0': 10 } },
            { round_num: 8, cards_dealt: 1, scores: { '0': 11 } },
            { round_num: 9, cards_dealt: 1, scores: { '0': -1 } },
            { round_num: 10, cards_dealt: 2, scores: { '0': 10 } },
        ];
        const totals = { '0': 30 };

        // Act
        const html = renderScoresheetTable(players, rounds, totals);

        // Assert — cards_dealt values appear in order, not round_nums
        const cellPattern = /<td>(\d+)<span/g;
        const cardCounts = [];
        let match;
        while ((match = cellPattern.exec(html)) !== null) {
            cardCounts.push(parseInt(match[1], 10));
        }
        expect(cardCounts).toEqual([2, 1, 1, 2]);
    });
});
