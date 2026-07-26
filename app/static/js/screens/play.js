// Play screen — trump display, round info, end round button

import { getGame, getBids, enterRoundEnd } from '../api.js';

export const playScreen = {
    async mount(container, state, { navigate, params }) {
        const gameId = params[0];
        const game = await getGame(gameId);
        state.game = game;

        const settings = game.settings;
        const mode = settings.mode || 'expert';
        const players = game.players;

        document.body.setAttribute('data-phase', 'playing');

        function getRoundCards(roundNum) {
            return 8 - ((roundNum - 1) % 8);
        }

        function getTrump(roundNum) {
            const suits = ['♠', '♦', '♣', '♥'];
            const names = ['Spades', 'Diamonds', 'Clubs', 'Hearts'];
            const index = (roundNum - 1) % 4;
            const isRed = index === 1 || index === 3;
            return { symbol: suits[index], name: names[index], isRed };
        }

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
            } catch { /* ignore */ }
        }

        container.innerHTML = `
            <div class="play">
                <div class="round-info">
                    <span>Round ${game.current_round} of ${game.total_rounds}</span>
                    <span>${cardsDealt} card${cardsDealt > 1 ? 's' : ''}</span>
                    ${state.playground ? `<span class="share-code-mini">${state.playground.share_code}</span>` : ''}
                </div>

                ${mode !== 'expert' ? `
                    <div class="trump-display ${trump.isRed ? 'trump-red' : ''}">
                        <span class="trump-symbol">${trump.symbol}</span>
                        <span class="trump-name">${trump.name}</span>
                    </div>
                ` : ''}

                <div class="play-info">
                    <p>Dealer: <strong>${dealerName}</strong></p>
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
            } catch (error) {
                alert(error.message);
            }
        });
    },

    unmount() {},
};
