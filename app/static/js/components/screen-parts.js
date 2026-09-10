/**
 * Shared UI fragments for game screens (bidding, play, roundend).
 * Each function does one thing — render HTML or attach a handler.
 */

import { endGame } from '../api.js';
import { getRoundCards, getTrump, escapeHtml } from './game-utils.js';

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
    const collapsed = localStorage.getItem('scokeep_island_collapsed') === '1';
    const cls = collapsed ? 'game-island island-collapsed' : 'game-island';
    const icon = collapsed ? '+' : '−';
    return `
        <div class="${cls}">
            <span>${escapeHtml(dealerName)} deals</span>
            <span class="island-sep">·</span>
            <span>${cardsDealt} card${cardsDealt > 1 ? 's' : ''}</span>
            <span class="island-sep">·</span>
            <span>R${game.current_round}/${game.total_rounds}</span>
            <button class="island-toggle">${icon}</button>
        </div>
    `;
}

/**
 * Attach the island toggle click handler inside a container.
 */
export function attachIslandToggle(container) {
    const toggle = container.querySelector('.island-toggle');
    if (!toggle) return;
    toggle.addEventListener('click', () => {
        const island = container.querySelector('.game-island');
        const isCollapsed = island.classList.toggle('island-collapsed');
        toggle.textContent = isCollapsed ? '+' : '−';
        localStorage.setItem('scokeep_island_collapsed', isCollapsed ? '1' : '0');
    });
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
        if (confirm('End this game? You can review scores before finalizing.')) {
            await endGame(gameId);
            navigate(`review/${gameId}`);
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

/**
 * Render a full scoresheet table (used by scoreboard game-over and review screen).
 * @param {string[]} players - Player names
 * @param {Array} rounds - Round data with scores
 * @param {Object} totals - Cumulative totals by player index
 * @param {function} [rowAttrs] - Optional fn(round) returning extra attributes for each <tr>
 */
export function renderScoresheetTable(players, rounds, totals, { rowAttrs } = {}) {
    return `
        <div class="score-table score-table-full">
            <table class="scoresheet">
                <thead>
                    <tr>
                        <th>R#</th>
                        ${players.map(name => `<th>${escapeHtml(name)}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
                    ${rounds.map(round => {
                        const trump = getTrump(round.round_num);
                        const extraAttrs = rowAttrs ? rowAttrs(round) : '';
                        return `<tr ${extraAttrs}>
                            <td>${round.round_num}<span class="${trump.isRed ? 'trump-red' : ''}" style="font-size:0.7em;">${trump.symbol}</span></td>
                            ${players.map((_, idx) => {
                                const roundScore = round.scores[String(idx)] || 0;
                                return `<td class="${roundScore < 0 ? 'score-negative' : ''}">
                                    ${roundScore > 0 ? '+' : ''}${roundScore}
                                </td>`;
                            }).join('')}
                        </tr>`;
                    }).join('')}
                </tbody>
                <tfoot>
                    <tr class="totals-row">
                        <td><strong>Tot</strong></td>
                        ${players.map((_, idx) => `<td><strong>${totals[String(idx)] || 0}</strong></td>`).join('')}
                    </tr>
                </tfoot>
            </table>
        </div>
    `;
}
