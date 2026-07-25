// Bidding screen — player queue + keypad + timer + confirm

import { getGame, submitBid, getBids, editBid, startRound } from '../api.js';
import { Keypad } from '../components/keypad.js';
import { Timer } from '../components/timer.js';

export const biddingScreen = {
    _timer: null,

    async mount(container, state, { navigate, params }) {
        const gameId = params[0];
        const game = await getGame(gameId);
        state.game = game;

        const players = game.players;
        const settings = game.settings;
        const timerSeconds = settings.timer_seconds || 10;
        const mustLose = settings.must_lose || false;
        const mode = settings.mode || 'expert';
        let currentPlayerIndex = 0;
        let bidsCollected = {};
        let phase = 'collecting';

        document.body.setAttribute('data-phase', 'bidding');

        // Load existing bids
        try {
            const roundData = await getBids(gameId);
            bidsCollected = roundData.bids || {};
            currentPlayerIndex = Object.keys(bidsCollected).length;
        } catch { /* no bids yet */ }

        const self = this;

        function getRoundCards(roundNum) {
            return 8 - ((roundNum - 1) % 8);
        }

        function getTrump(roundNum) {
            const suits = ['♠', '♦', '♣', '♥'];
            const index = (roundNum - 1) % 4;
            const isRed = index === 1 || index === 3; // diamonds, hearts
            return { symbol: suits[index], isRed };
        }

        function getDisabledKeys() {
            if (!mustLose) return [];
            // Only grey out for the last player to bid
            const isLastPlayer = currentPlayerIndex === players.length - 1;
            if (!isLastPlayer) return [];
            const cardsDealt = getRoundCards(game.current_round);
            const totalBids = Object.values(bidsCollected).reduce((sum, v) => sum + v, 0);
            const forbidden = cardsDealt - totalBids;
            if (forbidden >= 0 && forbidden <= cardsDealt) return [forbidden];
            return [];
        }

        function renderCollecting() {
            phase = 'collecting';
            if (currentPlayerIndex >= players.length) {
                renderConfirm();
                return;
            }

            const cardsDealt = getRoundCards(game.current_round);
            container.innerHTML = `
                <div class="bidding">
                    <div class="round-info">
                        <span>Round ${game.current_round} of ${game.total_rounds}</span>
                        <span>${cardsDealt} card${cardsDealt > 1 ? 's' : ''}</span>
                        ${mode !== 'expert' ? `<span class="trump ${getTrump(game.current_round).isRed ? 'trump-red' : ''}">${getTrump(game.current_round).symbol}</span>` : ''}
                    </div>
                    <div class="bid-player-name">${players[currentPlayerIndex]}</div>
                    <p class="bid-prompt">How many will you bid?</p>
                    <p class="claimed-info">${Object.values(bidsCollected).reduce((s, v) => s + v, 0)} of ${cardsDealt} hands claimed</p>
                    <div id="keypad-container"></div>
                    <p class="error hidden" id="bid-error"></p>
                </div>
            `;

            const keypad = Keypad({
                max: cardsDealt,
                disabled: getDisabledKeys(),
                onSelect: (value) => handleBidSelect(value),
            });
            container.querySelector('#keypad-container').appendChild(keypad);
        }

        function renderReview(playerIndex, value) {
            phase = 'reviewing';
            container.innerHTML = `
                <div class="bidding">
                    <div class="round-info">
                        <span>Round ${game.current_round} of ${game.total_rounds}</span>
                    </div>
                    <div class="bid-player-name">${players[playerIndex]}</div>
                    <div class="bid-value-display">${value}</div>
                    <div id="timer-container"></div>
                </div>
            `;

            if (self._timer) self._timer.destroy();

            const timerEl = Timer({
                seconds: timerSeconds,
                onExpire: () => advanceToNext(),
                onCancel: () => {
                    currentPlayerIndex = playerIndex;
                    delete bidsCollected[String(playerIndex)];
                    renderCollecting();
                },
            });
            self._timer = timerEl;
            container.querySelector('#timer-container').appendChild(timerEl);
        }

        function renderConfirm() {
            phase = 'confirming';
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
                        ${players.map((name, index) => `
                            <div class="bid-summary-row">
                                <span>${name}</span>
                                <span class="bid-summary-value">${bidsCollected[String(index)] ?? '?'}</span>
                                <button class="btn-small btn-edit" data-edit="${index}">Edit</button>
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
                    const index = parseInt(btn.dataset.edit);
                    currentPlayerIndex = index;
                    delete bidsCollected[String(index)];
                    renderCollecting();
                });
            });

            container.querySelector('#confirm-bids').addEventListener('click', async () => {
                const errorEl = container.querySelector('#bid-error');
                try {
                    await startRound(gameId);
                    navigate(`play/${gameId}`);
                } catch (error) {
                    errorEl.textContent = error.message;
                    errorEl.classList.remove('hidden');
                }
            });
        }

        async function handleBidSelect(value) {
            try {
                const playerKey = String(currentPlayerIndex);
                if (playerKey in bidsCollected) {
                    await editBid(gameId, currentPlayerIndex, value);
                } else {
                    await submitBid(gameId, currentPlayerIndex, value);
                }
                bidsCollected[playerKey] = value;
                renderReview(currentPlayerIndex, value);
            } catch (error) {
                const errorEl = container.querySelector('#bid-error');
                if (errorEl) {
                    errorEl.textContent = error.message;
                    errorEl.classList.remove('hidden');
                }
            }
        }

        function advanceToNext() {
            currentPlayerIndex++;
            renderCollecting();
        }

        renderCollecting();
    },

    unmount() {
        if (this._timer) {
            this._timer.destroy();
            this._timer = null;
        }
    },
};
