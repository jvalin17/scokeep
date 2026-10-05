/**
 * ScoreDialer state — buffer + Next semantics (Scoresheet).
 * Requirements: multi-game Score entry UX (buffer, ±, digit cap, debounce).
 */
import { describe, it, expect } from 'vitest';
import {
    createDialerState,
    pushDigit,
    backspace,
    toggleSign,
    clearBuffer,
    displayValue,
    parsedScore,
    canCommit,
    canAcceptNext,
} from '../../app/static/js/components/score-dialer.js';

describe('ScoreDialer state', () => {
    it('pushes digits into buffer without committing', () => {
        let state = createDialerState();
        state = pushDigit(state, '4');
        state = pushDigit(state, '2');
        expect(displayValue(state)).toBe('42');
        expect(canCommit(state)).toBe(true);
        expect(parsedScore(state)).toBe(42);
    });

    it('blocks empty commit and debounce Next', () => {
        const empty = createDialerState();
        expect(canCommit(empty)).toBe(false);
        expect(parsedScore(empty)).toBeNull();

        expect(canAcceptNext(0, 100, 400)).toBe(true);
        expect(canAcceptNext(100, 200, 400)).toBe(false);
        expect(canAcceptNext(100, 500, 400)).toBe(true);
    });

    it('enforces digit cap and sign toggle rules', () => {
        let state = createDialerState({ maxDigits: 4, allowNegatives: false });
        for (const digit of ['1', '2', '3', '4']) {
            state = pushDigit(state, digit);
        }
        const capped = pushDigit(state, '5');
        expect(displayValue(capped)).toBe('1234');
        expect(capped.flash).toBe('max_digits');

        const noSign = toggleSign(state);
        expect(displayValue(noSign)).toBe('1234');
        expect(noSign.negative).toBe(false);

        let neg = createDialerState({ allowNegatives: true });
        neg = pushDigit(neg, '1');
        neg = pushDigit(neg, '5');
        neg = toggleSign(neg);
        expect(displayValue(neg)).toBe('−15');
        expect(parsedScore(neg)).toBe(-15);
    });

    it('backspace and clear reset buffer', () => {
        let state = createDialerState({ allowNegatives: true });
        state = pushDigit(state, '9');
        state = toggleSign(state);
        state = backspace(state);
        expect(displayValue(state)).toBe('');
        expect(state.negative).toBe(false);

        state = pushDigit(state, '7');
        state = clearBuffer(state);
        expect(displayValue(state)).toBe('');
        expect(canCommit(state)).toBe(false);
    });

    it('leading zero replaced by next digit', () => {
        let state = createDialerState();
        state = pushDigit(state, '0');
        state = pushDigit(state, '5');
        expect(displayValue(state)).toBe('5');
    });
});
