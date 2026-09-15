/**
 * Phase state machine — pure JS port of Python GameService.advance_round / extend_game.
 *
 * Both functions are PURE: they return a new game state object and never
 * mutate the input. This makes them safe to call from any context (UI, tests,
 * workers) without side effects.
 *
 * Parity verified against: tests/vectors/phase_vectors.json
 */

const DEFAULT_ROUNDS_PER_SET = 8;

/**
 * Advance the game to the next round (or to review phase if all rounds are done).
 *
 * Port of GameService.advance_round (app/services/game.py).
 *
 * @param {Object} game - Current game state.
 * @param {number} game.current_round
 * @param {number} game.total_rounds
 * @param {number} game.dealer_index
 * @param {string[]} game.players
 * @param {string} game.phase
 * @returns {Object} New game state object (input is not mutated).
 */
export function advanceRound(game) {
    if (game.current_round >= game.total_rounds) {
        return { ...game, phase: 'review' };
    }
    return {
        ...game,
        current_round: game.current_round + 1,
        dealer_index: (game.dealer_index + 1) % game.players.length,
        phase: 'bidding',
    };
}

/**
 * Add another set to the game (extend beyond the originally planned total_rounds).
 *
 * Port of GameService.extend_game (app/services/game.py).
 *
 * @param {Object} game - Current game state.
 * @param {number} game.total_rounds
 * @param {Object} game.settings
 * @param {number} [game.settings.rounds_per_set] - Defaults to 8 if absent.
 * @param {number} [game.settings.num_sets] - Defaults to 3 if absent.
 * @returns {Object} New game state object (input and nested settings are not mutated).
 */
export function extendGame(game) {
    const roundsPerSet = game.settings.rounds_per_set ?? DEFAULT_ROUNDS_PER_SET;
    const numSets = (game.settings.num_sets ?? 3) + 1;
    return {
        ...game,
        total_rounds: game.total_rounds + roundsPerSet,
        settings: { ...game.settings, num_sets: numSets },
    };
}
