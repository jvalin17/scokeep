/**
 * ScoreDialer — pure buffer state for Scoresheet multi-digit entry.
 * No network, no DOM. Callers own player queue + IDB/sync.
 *
 * @typedef {object} DialerState
 * @property {string} digits
 * @property {boolean} negative
 * @property {boolean} allowNegatives
 * @property {number} maxDigits
 * @property {string|null} flash
 */

const MINUS_SIGN = '\u2212'; // −

/**
 * @param {{ allowNegatives?: boolean, maxDigits?: number }} [options]
 * @returns {DialerState}
 */
export function createDialerState({ allowNegatives = false, maxDigits = 4 } = {}) {
    return {
        digits: '',
        negative: false,
        allowNegatives: Boolean(allowNegatives),
        maxDigits: maxDigits,
        flash: null,
    };
}

/**
 * @param {DialerState} state
 * @param {string|number} digit
 * @returns {DialerState}
 */
export function pushDigit(state, digit) {
    const ch = String(digit);
    if (!/^[0-9]$/.test(ch)) {
        return { ...state, flash: null };
    }
    if (state.digits.length >= state.maxDigits) {
        return { ...state, flash: 'max_digits' };
    }
    let digits = state.digits;
    if (digits === '0') {
        digits = ch;
    } else {
        digits = digits + ch;
    }
    return { ...state, digits, flash: null };
}

/**
 * @param {DialerState} state
 * @returns {DialerState}
 */
export function backspace(state) {
    const digits = state.digits.slice(0, -1);
    return {
        ...state,
        digits,
        negative: digits ? state.negative : false,
        flash: null,
    };
}

/**
 * @param {DialerState} state
 * @returns {DialerState}
 */
export function toggleSign(state) {
    if (!state.allowNegatives) {
        return { ...state, flash: null };
    }
    return { ...state, negative: !state.negative, flash: null };
}

/**
 * @param {DialerState} state
 * @returns {DialerState}
 */
export function clearBuffer(state) {
    return {
        ...state,
        digits: '',
        negative: false,
        flash: null,
    };
}

/**
 * @param {DialerState} state
 * @returns {string}
 */
export function displayValue(state) {
    if (!state.digits) {
        return state.negative && state.allowNegatives ? MINUS_SIGN : '';
    }
    const prefix = state.negative && state.allowNegatives ? MINUS_SIGN : '';
    return prefix + state.digits;
}

/**
 * @param {DialerState} state
 * @returns {boolean}
 */
export function canCommit(state) {
    return state.digits.length > 0;
}

/**
 * @param {DialerState} state
 * @returns {number|null}
 */
export function parsedScore(state) {
    if (!canCommit(state)) {
        return null;
    }
    const value = parseInt(state.digits, 10);
    if (Number.isNaN(value)) {
        return null;
    }
    if (state.negative && state.allowNegatives) {
        return -value;
    }
    return value;
}

/**
 * Next-commit debounce — ignore presses within debounceMs of lastCommitAt.
 * @param {number} lastCommitAt
 * @param {number} now
 * @param {number} [debounceMs=400]
 * @returns {boolean}
 */
export function canAcceptNext(lastCommitAt, now, debounceMs = 400) {
    if (!lastCommitAt) {
        return true;
    }
    return now - lastCommitAt >= debounceMs;
}
