/**
 * scoreboard.js — Pure scoreboard totals computation.
 *
 * Ported from Python app/services/scoreboard.py compute_scoreboard().
 * Computes cumulative per-player totals from an array of scored round dicts.
 */

/**
 * Compute cumulative totals and round data from an array of scored rounds.
 *
 * Each round object must have a `scores` property: {playerKey: scoreInt, ...}.
 * Other fields (round_num, cards_dealt, trump_suit, bids, hands_won) are
 * passed through unchanged in the returned rounds array.
 *
 * @param {Array<{round_num: number, cards_dealt: number, trump_suit: string,
 *                bids: Object, hands_won: Object, scores: Object}>} rounds
 *   Array of scored round objects.
 * @param {number} playerCount
 *   Ensures players "0" through "playerCount-1" appear in totals (value 0).
 * @returns {{ totals: Object<string, number>, rounds: Array<Object> }}
 *   Object with cumulative totals map and passthrough rounds array.
 */
export function computeScoreboard(rounds, playerCount = 0) {
    const totals = {};
    const roundsData = [];

    for (const round of rounds) {
        roundsData.push({ ...round });
        for (const [playerKey, score] of Object.entries(round.scores)) {
            totals[playerKey] = (totals[playerKey] ?? 0) + score;
        }
    }

    for (let i = 0; i < playerCount; i++) {
        const key = String(i);
        if (!(key in totals)) {
            totals[key] = 0;
        }
    }

    return { totals, rounds: roundsData };
}
