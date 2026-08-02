/**
 * Shared entry-order utilities for bidding and round-end screens.
 * Eliminates duplicate entry-order calculation and player tracking.
 */

/**
 * Build the player entry order starting from the player after the dealer.
 * @param {number} dealerIndex - Index of the current dealer
 * @param {number} playerCount - Total number of players
 * @returns {number[]} Array of player indices in entry order
 */
export function getEntryOrder(dealerIndex, playerCount) {
    const order = [];
    for (let i = 1; i <= playerCount; i++) {
        order.push((dealerIndex + i) % playerCount);
    }
    return order;
}
