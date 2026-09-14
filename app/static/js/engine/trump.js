/**
 * Trump rotation and round-card utilities.
 *
 * Port of app/utils/trump.py — exact parity with Python implementation.
 */

const DECK_SIZE = 52;
const TRUMP_ORDER = ["spades", "diamonds", "clubs", "hearts"];
const DEFAULT_ROUNDS_PER_SET = 8;

/**
 * Maximum cards that can be dealt per round given a player count.
 * Uses integer (floor) division of deck size.
 *
 * @param {number} playerCount
 * @returns {number}
 */
export function maxCardsForPlayers(playerCount) {
  return Math.floor(DECK_SIZE / playerCount);
}

/**
 * Get the trump suit name for a given round number (1-based).
 * Rotates: spades → diamonds → clubs → hearts, repeating.
 *
 * @param {number} roundNum  1-based round number
 * @returns {string}  suit name, e.g. "spades"
 */
export function getTrumpForRound(roundNum) {
  return TRUMP_ORDER[(roundNum - 1) % TRUMP_ORDER.length];
}

/**
 * Get number of cards dealt in a given round.
 * Pattern alternates by set: odd sets descend (8→1), even sets ascend (1→8).
 *
 * @param {number} roundNum        1-based round number
 * @param {number} roundsPerSet    cards in a full set (default 8)
 * @returns {number}
 */
export function getCardsForRound(roundNum, roundsPerSet = DEFAULT_ROUNDS_PER_SET) {
  const positionInSet = (roundNum - 1) % roundsPerSet;
  const setNumber = Math.floor((roundNum - 1) / roundsPerSet); // 0-based
  if (setNumber % 2 === 0) {
    // Odd sets (1st, 3rd, ...): descend roundsPerSet→1
    return roundsPerSet - positionInSet;
  } else {
    // Even sets (2nd, 4th, ...): ascend 1→roundsPerSet
    return positionInSet + 1;
  }
}
