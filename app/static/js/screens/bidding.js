// Bidding screen — player queue + keypad + back button

import { submitBid, getBids, editBid, startRound, resyncGame, guardPhase } from '../api.js';
import { Keypad, InlineKeypad } from '../components/keypad.js';
import { getRoundCards, escapeHtml } from '../components/game-utils.js';
import { getEntryOrder } from '../components/entry-utils.js';
import { renderGameIsland, renderRoundInfoBar, renderTrumpDisplay, attachEndGameHandler, showError, setScreenContext } from '../components/screen-parts.js';
import { soundStartRound } from '../components/sounds.js';

export const biddingScreen = {
    async mount(container, state, { navigate, params }) {
        const gameId = params[0];
        const game = await guardPhase(gameId, 'bidding');
        if (!game) return;
        state.game = game;

        const players = game.players;
        const settings = game.settings;
        const mustLose = settings.must_lose || false;
        const mode = settings.mode || 'expert';
        const rps = settings.rounds_per_set || 8;
        const biddingOrder = getEntryOrder(game.dealer_index, players.length);
        let bidPosition = 0;
        let bidsCollected = {};
        let editingPi = null;
        const backendHasBid = new Set();

        setScreenContext('bidding', game);

        // Load existing bids
        try {
            const roundData = await getBids(gameId);
            bidsCollected = roundData.bids || {};
            bidPosition = Object.keys(bidsCollected).length;
            Object.keys(bidsCollected).forEach(key => backendHasBid.add(key));
        } catch { /* first round — no bids yet */ }

        function currentPlayer() { return biddingOrder[bidPosition]; }

        function getMustLoseDisabledKeys(playerIndex, cardsDealt) {
            if (!mustLose) return [];
            const lastPlayerIndex = biddingOrder[biddingOrder.length - 1];
            if (playerIndex !== lastPlayerIndex) return [];
            const totalOtherBids = Object.entries(bidsCollected)
                .filter(([key]) => key !== String(playerIndex))
                .reduce((sum, [, val]) => sum + val, 0);
            const forbidden = cardsDealt - totalOtherBids;
            if (forbidden >= 0 && forbidden <= cardsDealt) return [forbidden];
            return [];
        }

        function checkMustLoseCascade(cardsDealt) {
            if (!mustLose) return;
            const lastPlayerIndex = biddingOrder[biddingOrder.length - 1];
            const lastKey = String(lastPlayerIndex);
            if (!(lastKey in bidsCollected)) return;
            const totalOthers = Object.entries(bidsCollected)
                .filter(([key]) => key !== lastKey)
                .reduce((sum, [, val]) => sum + val, 0);
            if (totalOthers + bidsCollected[lastKey] === cardsDealt) {
                delete bidsCollected[lastKey];
            }
        }

        function renderCollecting() {
            if (bidPosition >= players.length) {
                renderConfirm();
                return;
            }

            const pi = currentPlayer();
            const cardsDealt = getRoundCards(game.current_round, rps);
            container.innerHTML = `
                <div class="bidding">
                    ${renderGameIsland(game, rps)}
                    ${renderRoundInfoBar(state)}
                    <div class="bid-player-name">${escapeHtml(players[pi])}</div>
                    <p class="bid-prompt">How many will you bid?</p>
                    <p class="claimed-info">${Object.values(bidsCollected).reduce((s, v) => s + v, 0)} / ${cardsDealt} claimed</p>
                    <div id="keypad-container"></div>
                    ${renderTrumpDisplay(game.current_round, mode)}
                    <div class="bid-nav">
                        ${bidPosition > 0 ? '<button id="go-back" class="btn btn-back">← Previous</button>' : ''}
                        ${String(pi) in bidsCollected && bidPosition < players.length - 1 ? '<button id="go-next" class="btn btn-back">Next →</button>' : ''}
                    </div>
                    <p class="error hidden" id="bid-error"></p>
                </div>
            `;

            const keypad = Keypad({
                max: cardsDealt,
                disabled: getMustLoseDisabledKeys(pi, cardsDealt),
                onSelect: (value) => handleBidSelect(value),
            });
            container.querySelector('#keypad-container').appendChild(keypad);

            const backBtn = container.querySelector('#go-back');
            if (backBtn) {
                backBtn.addEventListener('click', () => {
                    bidPosition--;
                    renderCollecting();
                });
            }

            const nextBtn = container.querySelector('#go-next');
            if (nextBtn) {
                nextBtn.addEventListener('click', () => {
                    bidPosition++;
                    renderCollecting();
                });
            }

            attachEndGameHandler(container, gameId, navigate, state);
        }

        function renderConfirm() {
            const cardsDealt = getRoundCards(game.current_round, rps);
            const allBidsPresent = biddingOrder.every(pi => String(pi) in bidsCollected);
            const totalBids = Object.values(bidsCollected).reduce((sum, v) => sum + v, 0);

            container.innerHTML = `
                <div class="bidding">
                    ${renderRoundInfoBar(state)}
                    <div class="round-info">
                        <span>Round ${game.current_round}</span>
                        <span>${cardsDealt} cards</span>
                    </div>
                    <h3>Confirm Bids</h3>
                    <div class="bid-summary">
                        ${biddingOrder.map(pi => {
                            const key = String(pi);
                            const hasBid = key in bidsCollected;
                            const isEditing = editingPi === pi;
                            const needsRebid = !hasBid && !isEditing;
                            return `
                                <div class="bid-summary-row ${needsRebid ? 'must-lose-warn' : ''}">
                                    <span>${escapeHtml(players[pi])}${pi === game.dealer_index ? ' (D)' : ''}</span>
                                    <span class="bid-summary-value">${hasBid ? bidsCollected[key] : '?'}</span>
                                    <button class="btn-small btn-edit" data-edit="${pi}">${isEditing ? 'Cancel' : 'Edit'}</button>
                                </div>
                                ${isEditing ? '<div id="inline-keypad-slot"></div>' : ''}
                            `;
                        }).join('')}
                    </div>
                    <div class="bid-total">
                        Total: ${totalBids} / ${cardsDealt}
                        ${allBidsPresent && totalBids === cardsDealt ? '<span class="overbid-warn">⚠ total = cards dealt</span>' : ''}
                    </div>
                    ${allBidsPresent ? '<button id="confirm-bids" class="btn btn-primary">Start Round</button>' : '<p class="claimed-info">Set missing bids to continue</p>'}
                    <p id="bid-error" class="error hidden"></p>
                </div>
            `;

            attachEndGameHandler(container, gameId, navigate, state);

            container.querySelectorAll('[data-edit]').forEach(btn => {
                btn.addEventListener('click', () => {
                    const pi = parseInt(btn.dataset.edit);
                    editingPi = (editingPi === pi) ? null : pi;
                    renderConfirm();
                });
            });

            const keypadSlot = container.querySelector('#inline-keypad-slot');
            if (keypadSlot && editingPi !== null) {
                const inlineKeypad = InlineKeypad({
                    max: cardsDealt,
                    disabled: getMustLoseDisabledKeys(editingPi, cardsDealt),
                    onSelect: async (value) => {
                        try {
                            await editBid(gameId, editingPi, value);
                            bidsCollected[String(editingPi)] = value;
                            editingPi = null;
                            checkMustLoseCascade(cardsDealt);
                            renderConfirm();
                        } catch (error) {
                            showError(container, 'bid-error', error.message);
                        }
                    },
                });
                keypadSlot.appendChild(inlineKeypad);
            }

            const confirmBtn = container.querySelector('#confirm-bids');
            if (confirmBtn) {
                confirmBtn.addEventListener('click', async () => {
                    try {
                        await startRound(gameId);
                        soundStartRound();
                        navigate(`play/${gameId}`);
                    } catch {
                        await resyncGame(gameId);
                    }
                });
            }
        }

        async function handleBidSelect(value) {
            const pi = currentPlayer();
            try {
                const playerKey = String(pi);
                if (backendHasBid.has(playerKey)) {
                    await editBid(gameId, pi, value);
                } else {
                    await submitBid(gameId, pi, value);
                    backendHasBid.add(playerKey);
                }
                bidsCollected[playerKey] = value;
                bidPosition++;
                renderCollecting();
            } catch (error) {
                showError(container, 'bid-error', error.message);
            }
        }

        renderCollecting();
    },

    unmount() {},
};
