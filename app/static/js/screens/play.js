// Play screen — trump display, round info, end round button

import { getGame, getBids, enterRoundEnd, endGame, resyncGame, guardPhase } from '../api.js';
import { getRoundCards, getTrump } from '../components/game-utils.js';
import { soundEndGame } from '../components/sounds.js';

export const playScreen = {
    async mount(container, state, { navigate, params }) {
        const gameId = params[0];
        const game = await guardPhase(gameId, 'playing');
        if (!game) return;
        state.game = game;

        const settings = game.settings;
        const mode = settings.mode || 'expert';
        const players = game.players;

        document.body.setAttribute('data-phase', 'playing');

        const cardsDealt = getRoundCards(game.current_round);
        const trump = getTrump(game.current_round);
        const dealerName = players[game.dealer_index];

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
            } catch (e) { console.warn('Failed to load bids:', e.message); }
        }

        container.innerHTML = `
            <div class="play">
                <div class="game-island">
                    <span>${dealerName} deals</span>
                    <span class="island-sep">·</span>
                    <span>${cardsDealt} card${cardsDealt > 1 ? 's' : ''}</span>
                    <span class="island-sep">·</span>
                    <span>R${game.current_round}/${game.total_rounds}</span>
                </div>
                <div class="round-info">
                    ${state.playground ? `<button class="btn-home" onclick="location.hash='playground/${state.playground.share_code}'">🏠</button>` : ''}
                    <button class="btn-end-game" id="end-game-btn">End Game</button>
                </div>

                ${mode !== 'expert' ? `
                    <div class="trump-display ${trump.isRed ? 'trump-red' : ''}">
                        <span class="trump-symbol">${trump.symbol}</span>
                        <span class="trump-name">${trump.name}</span>
                    </div>
                ` : ''}

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

        container.querySelector('#end-game-btn').addEventListener('click', async () => {
            if (confirm('End this game? Scores so far will be saved.')) {
                await endGame(gameId);
                soundEndGame();
                navigate(`scoreboard/${gameId}`);
            }
        });
    },

    unmount() {},
};
