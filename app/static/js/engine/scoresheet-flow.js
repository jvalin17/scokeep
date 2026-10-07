/**
 * Game flow maps — phase → hash screen.
 * Judgement keeps bid/play; Scoresheet never routes there.
 *
 * High-level loop (Scoresheet):
 *   lobby → entry → round_review → scoreboard|intermission → entry …
 *   → review → final
 */

/** @type {Record<string, string>} */
export const JUDGEMENT_PHASE_ROUTES = {
    bidding: 'bid',
    playing: 'play',
    round_end: 'roundend',
    scoring: 'scoreboard',
    scoreboard: 'scoreboard',
    review: 'review',
    final: 'final',
    finished: 'scoreboard',
};

/** @type {Record<string, string>} */
export const SCORESHEET_PHASE_ROUTES = {
    entry: 'entry',
    round_review: 'roundend',
    scoreboard: 'scoreboard',
    intermission: 'scoreboard',
    review: 'review',
    final: 'final',
    finished: 'scoreboard',
};

/** Happy-path phase cycle while scoring rounds (End Game leaves this loop). */
export const SCORESHEET_FLOW = ['entry', 'round_review', 'scoreboard', 'entry'];

const NEXT_SCORESHEET_PHASE = {
    entry: 'round_review',
    round_review: 'scoreboard',
    scoreboard: 'entry',
    intermission: 'entry',
};

/**
 * @param {object|null|undefined} game
 * @returns {boolean}
 */
export function isScoresheetGame(game) {
    return game?.settings?.game_type === 'scoresheet';
}

/**
 * @param {'kachuful'|'scoresheet'|string} gameType
 * @param {string} phase
 * @returns {string} hash screen name
 */
export function routeForPhase(gameType, phase) {
    const map =
        gameType === 'scoresheet' ? SCORESHEET_PHASE_ROUTES : JUDGEMENT_PHASE_ROUTES;
    return map[phase] || 'scoreboard';
}

/**
 * @param {{ phase?: string, settings?: { game_type?: string } }} game
 * @returns {string}
 */
export function routeForGame(game) {
    const gameType = game?.settings?.game_type || 'kachuful';
    return routeForPhase(gameType, game?.phase || '');
}

/**
 * @param {string} phase
 * @returns {string|null} next phase, or null if leaving the round loop
 */
export function nextScoresheetPhase(phase) {
    if (Object.prototype.hasOwnProperty.call(NEXT_SCORESHEET_PHASE, phase)) {
        return NEXT_SCORESHEET_PHASE[phase];
    }
    return null;
}
