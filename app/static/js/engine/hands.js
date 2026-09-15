/**
 * Hands validation engine.
 *
 * Ported from app/services/round.py RoundService.submit_hands.
 * Pure function — no side effects, no DOM access, no imports.
 */

/**
 * Validate a hands-won submission for one player.
 *
 * The player's own existing entry (if any) is excluded from the others sum,
 * so re-submissions are allowed and do not double-count.
 *
 * @param {Object.<string, number>} existingHands - Current hands_won map (keys are string player indices).
 * @param {number} playerIndex - Index of the player submitting.
 * @param {number} value - Number of hands the player claims to have won.
 * @param {number} cardsDealt - Total cards dealt this round.
 * @returns {null|string} null if valid, or an error message string if invalid.
 */
export function validateHands(existingHands, playerIndex, value, cardsDealt) {
  if (value < 0) {
    return `Hands (${value}) cannot be negative`;
  }
  const playerKey = String(playerIndex);
  let totalOthers = 0;
  for (const [k, v] of Object.entries(existingHands)) {
    if (k !== playerKey) {
      totalOthers += v;
    }
  }
  const remaining = cardsDealt - totalOthers;
  if (value > remaining) {
    return `Hands (${value}) exceeds remaining cards (${remaining})`;
  }
  return null;
}
