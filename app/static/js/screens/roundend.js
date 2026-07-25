// Round end screen — hands won entry via keypad + timer

import { getGame, submitHands, endRound } from '../api.js';
import { Keypad } from '../components/keypad.js';
import { Timer } from '../components/timer.js';

export const roundendScreen = {
    _timer: null,

    async mount(container, state, { navigate, params }) {
        const gameId = params[0];
        const game = await getGame(gameId);
        state.game = game;

        const players = game.players;
        const timerSeconds = game.settings.timer_seconds || 10;
        let currentPlayerIndex = 0;
        let handsCollected = {};

        document.body.setAttribute('data-phase', 'roundend');

        const self = this;

        function getRoundCards(roundNum) {
            return 8 - ((roundNum - 1) % 8);
        }

        function renderCollecting() {
            if (currentPlayerIndex >= players.length) {
                renderConfirm();
                return;
            }

            const cardsDealt = getRoundCards(game.current_round);
            container.innerHTML = `
                <div class="roundend">
                    <div class="round-info">
                        <span>Round ${game.current_round}</span>
                        <span>Scoring</span>
                    </div>
                    <div class="bid-player-name">${players[currentPlayerIndex]}</div>
                    <p class="bid-prompt">How many hands did they make?</p>
                    <div id="keypad-container"></div>
                    <p class="error hidden" id="hands-error"></p>
                </div>
            `;

            const keypad = Keypad({
                max: cardsDealt,
                disabled: [],
                onSelect: (value) => handleHandsSelect(value),
            });
            container.querySelector('#keypad-container').appendChild(keypad);
        }

        function renderReview(playerIndex, value) {
            container.innerHTML = `
                <div class="roundend">
                    <div class="round-info">
                        <span>Round ${game.current_round}</span>
                        <span>Scoring</span>
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
                    delete handsCollected[String(playerIndex)];
                    renderCollecting();
                },
            });
            self._timer = timerEl;
            container.querySelector('#timer-container').appendChild(timerEl);
        }

        function renderConfirm() {
            const cardsDealt = getRoundCards(game.current_round);
            const totalHands = Object.values(handsCollected).reduce((sum, v) => sum + v, 0);
            const mismatch = totalHands !== cardsDealt;

            container.innerHTML = `
                <div class="roundend">
                    <div class="round-info">
                        <span>Round ${game.current_round}</span>
                    </div>
                    <h3>Confirm Hands Won</h3>
                    <div class="bid-summary">
                        ${players.map((name, index) => `
                            <div class="bid-summary-row">
                                <span>${name}</span>
                                <span class="bid-summary-value">${handsCollected[String(index)] ?? '?'}</span>
                            </div>
                        `).join('')}
                    </div>
                    <div class="bid-total ${mismatch ? 'mismatch-warn' : ''}">
                        Total: ${totalHands} / ${cardsDealt}
                        ${mismatch ? '<span class="overbid-warn">⚠ Does not match cards dealt</span>' : ''}
                    </div>
                    <button id="score-round" class="btn btn-primary">Score Round</button>
                    <p id="score-error" class="error hidden"></p>
                </div>
            `;

            container.querySelector('#score-round').addEventListener('click', async () => {
                const errorEl = container.querySelector('#score-error');
                try {
                    await endRound(gameId);
                    navigate(`scoreboard/${gameId}`);
                } catch (error) {
                    errorEl.textContent = error.message;
                    errorEl.classList.remove('hidden');
                }
            });
        }

        async function handleHandsSelect(value) {
            try {
                await submitHands(gameId, currentPlayerIndex, value);
                handsCollected[String(currentPlayerIndex)] = value;
                renderReview(currentPlayerIndex, value);
            } catch (error) {
                const errorEl = container.querySelector('#hands-error');
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
