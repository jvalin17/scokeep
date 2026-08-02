// Round end screen — hands won entry via keypad + back button

import { submitHands, endRound, resyncGame, guardPhase } from '../api.js';
import { Keypad } from '../components/keypad.js';
import { getRoundCards } from '../components/game-utils.js';
import { getEntryOrder } from '../components/entry-utils.js';
import { renderGameIsland, renderRoundInfoBar, renderTrumpDisplay, attachEndGameHandler, showError } from '../components/screen-parts.js';
import { soundScoreRound } from '../components/sounds.js';

export const roundendScreen = {
    async mount(container, state, { navigate, params }) {
        const gameId = params[0];
        const game = await guardPhase(gameId, 'round_end');
        if (!game) return;
        state.game = game;

        const players = game.players;
        const rps = game.settings.rounds_per_set || 8;
        const mode = game.settings.mode || 'expert';
        const entryOrder = getEntryOrder(game.dealer_index, players.length);
        let entryPosition = 0;
        let handsCollected = {};

        document.body.setAttribute('data-phase', 'roundend');

        function currentPlayer() { return entryOrder[entryPosition]; }

        function getRemainingCards() {
            const cardsDealt = getRoundCards(game.current_round, rps);
            const totalHands = Object.values(handsCollected).reduce((s, v) => s + v, 0);
            return Math.max(0, cardsDealt - totalHands);
        }

        function getLastPlayerDisabledKeys() {
            const isLastPlayer = entryPosition === players.length - 1;
            if (!isLastPlayer) return [];
            const remaining = getRemainingCards();
            const cardsDealt = getRoundCards(game.current_round, rps);
            const disabled = [];
            for (let i = 0; i <= cardsDealt; i++) {
                if (i !== remaining) disabled.push(i);
            }
            return disabled;
        }

        function renderCollecting() {
            if (entryPosition >= players.length) {
                renderConfirm();
                return;
            }

            const pi = currentPlayer();
            const cardsDealt = getRoundCards(game.current_round, rps);
            const totalHands = Object.values(handsCollected).reduce((s, v) => s + v, 0);
            const isLastPlayer = entryPosition === players.length - 1;

            container.innerHTML = `
                <div class="roundend">
                    ${renderGameIsland(game, rps)}
                    ${renderRoundInfoBar(state)}
                    <div class="bid-player-name">${players[pi]}</div>
                    <p class="bid-prompt">How many hands did they make?</p>
                    <p class="claimed-info">${totalHands} of ${cardsDealt} hands accounted${isLastPlayer ? ` — must be ${cardsDealt - totalHands}` : ''}</p>
                    <div id="keypad-container"></div>
                    ${renderTrumpDisplay(game.current_round, mode)}
                    ${entryPosition > 0 ? '<button id="go-back" class="btn btn-back">← Previous Player</button>' : ''}
                    <p class="error hidden" id="hands-error"></p>
                </div>
            `;

            const keypad = Keypad({
                max: getRemainingCards(),
                disabled: getLastPlayerDisabledKeys(),
                onSelect: (value) => handleHandsSelect(value),
            });
            container.querySelector('#keypad-container').appendChild(keypad);

            const backBtn = container.querySelector('#go-back');
            if (backBtn) {
                backBtn.addEventListener('click', async () => {
                    entryPosition--;
                    const prevPi = currentPlayer();
                    // Reset previous player's hands on backend so remaining recalculates
                    await submitHands(gameId, prevPi, 0);
                    delete handsCollected[String(prevPi)];
                    renderCollecting();
                });
            }

            attachEndGameHandler(container, gameId, navigate);
        }

        function renderConfirm() {
            const cardsDealt = getRoundCards(game.current_round, rps);
            const totalHands = Object.values(handsCollected).reduce((sum, v) => sum + v, 0);

            container.innerHTML = `
                <div class="roundend">
                    <div class="round-info">
                        <span>Round ${game.current_round}</span>
                    </div>
                    <h3>Confirm Hands Won</h3>
                    <div class="bid-summary">
                        ${entryOrder.map(pi => `
                            <div class="bid-summary-row">
                                <span>${players[pi]}${pi === game.dealer_index ? ' (D)' : ''}</span>
                                <span class="bid-summary-value">${handsCollected[String(pi)] ?? '?'}</span>
                                <button class="btn-small btn-edit" data-edit="${pi}">Edit</button>
                            </div>
                        `).join('')}
                    </div>
                    <div class="bid-total">
                        Total: ${totalHands} / ${cardsDealt} ✓
                    </div>
                    <button id="score-round" class="btn btn-primary">Score Round</button>
                    <p id="score-error" class="error hidden"></p>
                </div>
            `;

            container.querySelectorAll('[data-edit]').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const pi = parseInt(btn.dataset.edit);
                    const pos = entryOrder.indexOf(pi);
                    // Reset hands on backend for this player and all after
                    for (let i = pos; i < entryOrder.length; i++) {
                        const clearKey = String(entryOrder[i]);
                        if (clearKey in handsCollected) {
                            await submitHands(gameId, entryOrder[i], 0);
                            delete handsCollected[clearKey];
                        }
                    }
                    entryPosition = pos;
                    renderCollecting();
                });
            });

            container.querySelector('#score-round').addEventListener('click', async () => {
                try {
                    await endRound(gameId);
                    soundScoreRound();
                    navigate(`scoreboard/${gameId}`);
                } catch {
                    await resyncGame(gameId);
                }
            });
        }

        async function handleHandsSelect(value) {
            const pi = currentPlayer();
            try {
                await submitHands(gameId, pi, value);
                handsCollected[String(pi)] = value;
                entryPosition++;
                renderCollecting();
            } catch (error) {
                showError(container, 'hands-error', error.message);
            }
        }

        renderCollecting();
    },

    unmount() {},
};
