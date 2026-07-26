/**
 * Shared game utility functions — trump, round cards, HTML escaping.
 * Fixes BUG-007 (DRY: getTrump/getRoundCards duplicated in 3 files)
 * Fixes BUG-002 (frontend: HTML escape for dynamic content)
 */

export function getRoundCards(roundNum, roundsPerSet = 8) {
    const positionInSet = (roundNum - 1) % roundsPerSet;
    const setNumber = Math.floor((roundNum - 1) / roundsPerSet); // 0-based
    if (setNumber % 2 === 0) {
        // Odd sets (1st, 3rd, ...): descend 8→1
        return roundsPerSet - positionInSet;
    } else {
        // Even sets (2nd, 4th, ...): ascend 1→8
        return positionInSet + 1;
    }
}

export function getTrump(roundNum) {
    const suits = ['♠', '♦', '♣', '♥'];
    const names = ['Spades', 'Diamonds', 'Chidi', 'Hearts'];
    const index = (roundNum - 1) % 4;
    const isRed = index === 1 || index === 3;
    return { symbol: suits[index], name: names[index], isRed };
}

export function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
