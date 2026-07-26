/**
 * Shared game utility functions — trump, round cards, HTML escaping.
 * Fixes BUG-007 (DRY: getTrump/getRoundCards duplicated in 3 files)
 * Fixes BUG-002 (frontend: HTML escape for dynamic content)
 */

export function getRoundCards(roundNum) {
    return 8 - ((roundNum - 1) % 8);
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
