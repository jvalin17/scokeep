/**
 * Shared UI fragments for game screens (bidding, play, roundend).
 * Each function does one thing — render HTML or attach a handler.
 */

import { endGame } from '../api.js';
import { getRoundCards, getTrump } from './game-utils.js';
import { soundEndGame } from './sounds.js';

/**
 * Set the phase and appearance on document.body for CSS styling.
 */
export function setScreenContext(phase, game) {
    document.body.setAttribute('data-phase', phase);
    if (game && game.settings) {
        document.body.setAttribute('data-appearance', game.settings.appearance || 'standard');
    }
}

/**
 * Render the floating game-island bar (dealer, cards, round counter).
 */
export function renderGameIsland(game, roundsPerSet) {
    const cardsDealt = getRoundCards(game.current_round, roundsPerSet);
    const dealerName = game.players[game.dealer_index];
    return `
        <div class="game-island">
            <span>${dealerName} deals</span>
            <span class="island-sep">·</span>
            <span>${cardsDealt} card${cardsDealt > 1 ? 's' : ''}</span>
            <span class="island-sep">·</span>
            <span>R${game.current_round}/${game.total_rounds}</span>
        </div>
    `;
}

/**
 * Render the round-info bar with optional home button and End Game button.
 */
export function renderRoundInfoBar(state) {
    return `
        <div class="round-info">
            ${state.playground ? `<button class="btn-home" data-nav="playground/${state.playground.share_code}">🏠</button>` : ''}
            <button class="btn-end-game" id="end-game-btn">End Game</button>
        </div>
    `;
}

/**
 * Render the trump display (shown in rookie/friendly modes).
 * @param {number} roundNum - Current round number
 * @param {string} mode - Game mode (expert/rookie/friendly)
 * @param {string} [size='small'] - 'small' for below-keypad, 'large' for play screen
 */
export function renderTrumpDisplay(roundNum, mode, size = 'small') {
    if (mode === 'expert') return '';
    const trump = getTrump(roundNum);
    if (size === 'large') {
        return `
            <div class="trump-display ${trump.isRed ? 'trump-red' : ''}">
                <span class="trump-symbol">${trump.symbol}</span>
                <span class="trump-name">${trump.name}</span>
            </div>
        `;
    }
    return `
        <div class="trump-below ${trump.isRed ? 'trump-red' : ''}">
            <span class="trump-symbol-sm">${trump.symbol}</span>
            <span class="trump-label">${trump.name}</span>
        </div>
    `;
}

/**
 * Attach the End Game click handler to #end-game-btn in the container.
 */
export function attachEndGameHandler(container, gameId, navigate, state) {
    // Bind data-nav buttons (replaces inline onclick)
    container.querySelectorAll('[data-nav]').forEach(el => {
        el.addEventListener('click', () => { location.hash = el.dataset.nav; });
    });

    const btn = container.querySelector('#end-game-btn');
    if (!btn) return;
    btn.addEventListener('click', async () => {
        if (confirm('End this game? Scores so far will be saved.')) {
            await endGame(gameId);
            soundEndGame();
            navigate(`scoreboard/${gameId}`);
        }
    });
}

/**
 * Show an error message in a .error element inside the container.
 */
export function showError(container, selectorId, message) {
    const errorEl = container.querySelector(`#${selectorId}`);
    if (!errorEl) return;
    errorEl.textContent = message;
    errorEl.classList.remove('hidden');
}
