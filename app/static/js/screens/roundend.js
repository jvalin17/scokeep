// Round end screen — hands won entry via keypad + back button

import { getGame, submitHands, endRound } from '../api.js';
import { Keypad } from '../components/keypad.js';

export const roundendScreen = {
    async mount(container, state, { navigate, params }) {
        const gameId = params[0];
        const game = await getGame(gameId);
        state.game = game;

        const players = game.players;
        // Hands entry order: start from player after dealer, same as bidding
        const entryOrder = [];
        for (let i = 1; i <= players.length; i++) {
            entryOrder.push((game.dealer_index + i) % players.length);
        }
        let entryPosition = 0;
        let handsCollected = {};

        document.body.setAttribute('data-phase', 'roundend');

        function currentPlayer() { return entryOrder[entryPosition]; }

        function getRoundCards(roundNum) {
            return 8 - ((roundNum - 1) % 8);
        }

        function getDisabledKeys() {
            const isLastPlayer = entryPosition === players.length - 1;
            if (!isLastPlayer) return [];
            const cardsDealt = getRoundCards(game.current_round);
            const totalHands = Object.values(handsCollected).reduce((s, v) => s + v, 0);
            const remaining = cardsDealt - totalHands;
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
            const cardsDealt = getRoundCards(game.current_round);
            const totalHands = Object.values(handsCollected).reduce((s, v) => s + v, 0);
            const isLastPlayer = entryPosition === players.length - 1;

            container.innerHTML = `
                <div class="roundend">
                    <div class="round-info">
                        <span>Round ${game.current_round}</span>
                        <span>Scoring</span>
                        ${state.playground ? `<span class="share-code-mini">${state.playground.share_code}</span>` : ''}
                    </div>
                    <div class="bid-player-name">${players[pi]}</div>
                    <p class="bid-prompt">How many hands did they make?</p>
                    <p class="claimed-info">${totalHands} of ${cardsDealt} hands accounted${isLastPlayer ? ` — must be ${cardsDealt - totalHands}` : ''}</p>
                    <div id="keypad-container"></div>
                    ${entryPosition > 0 ? '<button id="go-back" class="btn btn-back">← Previous Player</button>' : ''}
                    <p class="error hidden" id="hands-error"></p>
                </div>
            `;

            const keypad = Keypad({
                max: cardsDealt,
                disabled: getDisabledKeys(),
                onSelect: (value) => handleHandsSelect(value),
            });
            container.querySelector('#keypad-container').appendChild(keypad);

            const backBtn = container.querySelector('#go-back');
            if (backBtn) {
                backBtn.addEventListener('click', () => {
                    entryPosition--;
                    const prevPi = currentPlayer();
                    delete handsCollected[String(prevPi)];
                    renderCollecting();
                });
            }
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
                        ${entryOrder.map(pi => `
                            <div class="bid-summary-row">
                                <span>${players[pi]}${pi === game.dealer_index ? ' (D)' : ''}</span>
                                <span class="bid-summary-value">${handsCollected[String(pi)] ?? '?'}</span>
                                <button class="btn-small btn-edit" data-edit="${pi}">Edit</button>
                            </div>
                        `).join('')}
                    </div>
                    <div class="bid-total ${mismatch ? 'mismatch-warn' : ''}">
                        Total: ${totalHands} / ${cardsDealt}
                        ${mismatch ? '<span class="overbid-warn">⚠ Does not match cards dealt</span>' : '✓'}
                    </div>
                    <button id="score-round" class="btn btn-primary">Score Round</button>
                    <p id="score-error" class="error hidden"></p>
                </div>
            `;

            container.querySelectorAll('[data-edit]').forEach(btn => {
                btn.addEventListener('click', () => {
                    const pi = parseInt(btn.dataset.edit);
                    const pos = entryOrder.indexOf(pi);
                    for (let i = pos; i < entryOrder.length; i++) {
                        delete handsCollected[String(entryOrder[i])];
                    }
                    entryPosition = pos;
                    renderCollecting();
                });
            });

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
            const pi = currentPlayer();
            try {
                await submitHands(gameId, pi, value);
                handsCollected[String(pi)] = value;
                entryPosition++;
                renderCollecting();
            } catch (error) {
                const errorEl = container.querySelector('#hands-error');
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
