// Bidding screen — player queue + keypad + back button

import { getGame, submitBid, getBids, editBid, startRound } from '../api.js';
import { Keypad } from '../components/keypad.js';
import { soundStartRound } from '../components/sounds.js';

export const biddingScreen = {
    async mount(container, state, { navigate, params }) {
        const gameId = params[0];
        const game = await getGame(gameId);
        state.game = game;

        const players = game.players;
        const settings = game.settings;
        const mustLose = settings.must_lose || false;
        const mode = settings.mode || 'expert';
        // Bidding order: start from player after dealer, wrap around
        const biddingOrder = [];
        for (let i = 1; i <= players.length; i++) {
            biddingOrder.push((game.dealer_index + i) % players.length);
        }
        let bidPosition = 0;
        let bidsCollected = {};

        document.body.setAttribute('data-phase', 'bidding');

        // Load existing bids
        try {
            const roundData = await getBids(gameId);
            bidsCollected = roundData.bids || {};
            bidPosition = Object.keys(bidsCollected).length;
        } catch { /* no bids yet */ }

        function getRoundCards(roundNum) {
            return 8 - ((roundNum - 1) % 8);
        }

        function getTrump(roundNum) {
            const suits = ['♠', '♦', '♣', '♥'];
            const names = ['Spades', 'Diamonds', 'Chidi', 'Hearts'];
            const index = (roundNum - 1) % 4;
            const isRed = index === 1 || index === 3;
            return { symbol: suits[index], name: names[index], isRed };
        }

        function currentPlayer() { return biddingOrder[bidPosition]; }

        function getDisabledKeys() {
            if (!mustLose) return [];
            const isLastPlayer = bidPosition === players.length - 1;
            if (!isLastPlayer) return [];
            const cardsDealt = getRoundCards(game.current_round);
            const totalBids = Object.values(bidsCollected).reduce((sum, v) => sum + v, 0);
            const forbidden = cardsDealt - totalBids;
            if (forbidden >= 0 && forbidden <= cardsDealt) return [forbidden];
            return [];
        }

        function renderCollecting() {
            if (bidPosition >= players.length) {
                renderConfirm();
                return;
            }

            const pi = currentPlayer();
            const cardsDealt = getRoundCards(game.current_round);
            const trumpInfo = getTrump(game.current_round);
            const dealerName = players[game.dealer_index];
            container.innerHTML = `
                <div class="bidding">
                    <div class="round-info">
                        <span>Round ${game.current_round} of ${game.total_rounds}</span>
                        <span>${cardsDealt} card${cardsDealt > 1 ? 's' : ''}</span>
                        ${state.playground ? `<span class="share-code-mini">${state.playground.share_code}</span>` : ''}
                        <button class="btn-refresh" onclick="window.dispatchEvent(new HashChangeEvent('hashchange'))">↻</button>
                    </div>
                    <div class="bid-player-name">${players[pi]}</div>
                    <p class="bid-prompt">How many will you bid?</p>
                    ${mode === 'friendly' ? `<p class="claimed-info">${Object.values(bidsCollected).reduce((s, v) => s + v, 0)} of ${cardsDealt} hands claimed</p>` : ''}
                    <div id="keypad-container"></div>
                    ${mode !== 'expert' ? `<div class="trump-below ${trumpInfo.isRed ? 'trump-red' : ''}"><span class="trump-symbol-sm">${trumpInfo.symbol}</span><span class="trump-label">${trumpInfo.name}</span></div>` : ''}
                    <p class="dealer-info">Dealer: <strong>${dealerName}</strong></p>
                    ${bidPosition > 0 ? '<button id="go-back" class="btn btn-back">← Previous Player</button>' : ''}
                    <p class="error hidden" id="bid-error"></p>
                </div>
            `;

            const keypad = Keypad({
                max: cardsDealt,
                disabled: getDisabledKeys(),
                onSelect: (value) => handleBidSelect(value),
            });
            container.querySelector('#keypad-container').appendChild(keypad);

            const backBtn = container.querySelector('#go-back');
            if (backBtn) {
                backBtn.addEventListener('click', () => {
                    bidPosition--;
                    const prevPi = currentPlayer();
                    delete bidsCollected[String(prevPi)];
                    renderCollecting();
                });
            }
        }

        function renderConfirm() {
            const cardsDealt = getRoundCards(game.current_round);
            const totalBids = Object.values(bidsCollected).reduce((sum, v) => sum + v, 0);

            container.innerHTML = `
                <div class="bidding">
                    <div class="round-info">
                        <span>Round ${game.current_round}</span>
                        <span>${cardsDealt} cards</span>
                    </div>
                    <h3>Confirm Bids</h3>
                    <div class="bid-summary">
                        ${biddingOrder.map(pi => `
                            <div class="bid-summary-row">
                                <span>${players[pi]}${pi === game.dealer_index ? ' (D)' : ''}</span>
                                <span class="bid-summary-value">${bidsCollected[String(pi)] ?? '?'}</span>
                                <button class="btn-small btn-edit" data-edit="${pi}">Edit</button>
                            </div>
                        `).join('')}
                    </div>
                    <div class="bid-total">
                        Total: ${totalBids} / ${cardsDealt}
                        ${totalBids === cardsDealt ? '<span class="overbid-warn">= cards dealt</span>' : ''}
                    </div>
                    <button id="confirm-bids" class="btn btn-primary">Start Round</button>
                    <p id="bid-error" class="error hidden"></p>
                </div>
            `;

            container.querySelectorAll('[data-edit]').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const pi = parseInt(btn.dataset.edit);
                    delete bidsCollected[String(pi)];
                    bidPosition = biddingOrder.indexOf(pi);
                    renderCollecting();
                });
            });

            container.querySelector('#confirm-bids').addEventListener('click', async () => {
                const errorEl = container.querySelector('#bid-error');
                try {
                    await startRound(gameId);
                    soundStartRound();
                    navigate(`play/${gameId}`);
                } catch (error) {
                    errorEl.textContent = error.message;
                    errorEl.classList.remove('hidden');
                }
            });
        }

        async function handleBidSelect(value) {
            const pi = currentPlayer();
            try {
                const playerKey = String(pi);
                if (playerKey in bidsCollected) {
                    await editBid(gameId, pi, value);
                } else {
                    await submitBid(gameId, pi, value);
                }
                bidsCollected[playerKey] = value;
                bidPosition++;
                renderCollecting();
            } catch (error) {
                const errorEl = container.querySelector('#bid-error');
                if (errorEl) {
                    errorEl.textContent = error.message;
                    errorEl.classList.remove('hidden');
                }
            }
        }

        renderCollecting();
    },

    unmount() {},
};
