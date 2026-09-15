/**
 * bid.js — Pure bid validation logic (no side effects).
 *
 * Ported from Python: app/services/round.py → validate_bid()
 * Kept in sync with the shared test vectors: tests/vectors/bid_vectors.json
 *
 * All functions are exported for testability.
 */

/**
 * Validate a bid submission against game rules.
 *
 * @param {Object.<string, number>} existingBids
 *   Map of str(playerIndex) → bid value for bids already placed this round.
 * @param {number} playerIndex  Index of the player submitting this bid.
 * @param {number} value        The bid value being submitted.
 * @param {object} options
 * @param {boolean} options.mustLose     Whether must-lose mode is active.
 * @param {number}  options.cardsDeal    Number of cards dealt this round.
 * @param {number}  options.playerCount  Total number of players in the game.
 * @returns {string|null}
 *   null if the bid is valid; a non-empty error string describing the problem otherwise.
 */
export function validateBid(existingBids, playerIndex, value, { mustLose, cardsDeal, playerCount }) {
    if (value < 0) {
        return `Bid ${value} is invalid: bid cannot be negative`;
    }

    if (cardsDeal > 0 && value > cardsDeal) {
        return `Bid ${value} is invalid: bid cannot exceed cards dealt (${cardsDeal})`;
    }

    const playerKey = String(playerIndex);
    if (Object.prototype.hasOwnProperty.call(existingBids, playerKey)) {
        return `Bid already submitted for player ${playerIndex}`;
    }

    if (mustLose) {
        const bidsSOFar = Object.keys(existingBids).length;
        const isLastPlayer = bidsSOFar === playerCount - 1;
        if (isLastPlayer) {
            const existingTotal = Object.values(existingBids).reduce((sum, v) => sum + v, 0);
            if (existingTotal + value === cardsDeal) {
                return (
                    `Bid ${value} rejected: must-lose mode — ` +
                    `total bids (${existingTotal + value}) ` +
                    `cannot equal cards dealt (${cardsDeal})`
                );
            }
        }
    }

    return null;
}
