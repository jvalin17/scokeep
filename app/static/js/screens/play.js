// Play screen — trump display, round info, end round button

import { getBids, enterRoundEnd, resyncGame, guardPhase } from '../api.js';
import { getRoundCards } from '../components/game-utils.js';
import { renderGameIsland, renderRoundInfoBar, renderTrumpDisplay, attachEndGameHandler } from '../components/screen-parts.js';

export const playScreen = {
    async mount(container, state, { navigate, params }) {
        const gameId = params[0];
        const game = await guardPhase(gameId, 'playing');
        if (!game) return;
        state.game = game;

        const settings = game.settings;
        const mode = settings.mode || 'expert';
        const players = game.players;
        const rps = settings.rounds_per_set || 8;

        document.body.setAttribute('data-phase', 'playing');

        let bidsHtml = '';
        if (mode === 'friendly') {
            try {
                const roundData = await getBids(gameId);
                const bids = roundData.bids || {};
                bidsHtml = `
                    <div class="play-bids">
                        <h3>Bids</h3>
                        ${players.map((name, index) => `
                            <div class="play-bid-row">
                                <span>${name}</span>
                                <span class="play-bid-value">${bids[String(index)] ?? '-'}</span>
                            </div>
                        `).join('')}
                    </div>
                `;
            } catch { /* bids not available */ }
        }

        container.innerHTML = `
            <div class="play">
                ${renderGameIsland(game, rps)}
                ${renderRoundInfoBar(state)}
                ${renderTrumpDisplay(game.current_round, mode, 'large')}
                <div class="play-info">
                    ${mode === 'expert' ? '<p class="play-minimal">Play your round</p>' : ''}
                </div>
                ${bidsHtml}
                <button id="end-round-btn" class="btn btn-primary btn-large">End Round</button>
            </div>
        `;

        container.querySelector('#end-round-btn').addEventListener('click', async () => {
            try {
                await enterRoundEnd(gameId);
                navigate(`roundend/${gameId}`);
            } catch {
                await resyncGame(gameId);
            }
        });

        attachEndGameHandler(container, gameId, navigate);
    },

    unmount() {},
};
