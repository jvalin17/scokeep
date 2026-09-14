/**
 * Pluggable scoring engine for card games.
 *
 * Each formula takes a bid and actual hands won, returns points.
 * Formulas are registered in SCORING_FORMULAS map.
 *
 * Ported from app/services/scoring.py — exact logic, no simplification.
 */

/**
 * Kachuful standard scoring.
 *
 * Bid 0 made = 10, Bid 1 made = 11, Bid N>=2 made = N*10.
 * Miss = same value negated.
 *
 * @param {number} bid
 * @param {number} actual
 * @returns {number}
 */
export function kachufulStandard(bid, actual) {
  if (bid === actual) {
    if (bid === 0) return 10;
    else if (bid === 1) return 11;
    else return bid * 10;
  } else {
    if (bid === 0) return -10;
    else if (bid === 1) return -11;
    else return -(bid * 10);
  }
}

/**
 * Kachuful zeros scoring.
 *
 * Same as standard but bid 1 made = 10 (not 11).
 * Bid 0 and 1 are treated equally: made = 10, missed = -10.
 * Bid N>=2 made = N*10, missed = -(N*10).
 *
 * @param {number} bid
 * @param {number} actual
 * @returns {number}
 */
export function kachufulZeros(bid, actual) {
  if (bid === actual) {
    if (bid <= 1) return 10;
    return bid * 10;
  } else {
    if (bid <= 1) return -10;
    return -(bid * 10);
  }
}

const SCORING_FORMULAS = {
  kachuful_standard: kachufulStandard,
  kachuful_zeros: kachufulZeros,
};

/**
 * Calculate scores for all players in a round.
 *
 * @param {Object.<string, number>} bids - player_index -> bid
 * @param {Object.<string, number>} hands_won - player_index -> hands won
 * @param {string} formula_name - one of the registered formula names
 * @returns {Object.<string, number>} player_index -> score
 * @throws {Error} if formula_name is not registered
 */
export function calculateRoundScores(bids, hands_won, formula_name) {
  if (!(formula_name in SCORING_FORMULAS)) {
    throw new Error(`Unknown scoring formula: ${formula_name}`);
  }
  const formula = SCORING_FORMULAS[formula_name];
  const result = {};
  for (const player_index of Object.keys(bids)) {
    result[player_index] = formula(bids[player_index], hands_won[player_index]);
  }
  return result;
}
