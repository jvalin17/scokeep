// Round end screen — hands won entry via keypad + back button

import { submitHands, endRound, endGame, resyncGame, guardPhase } from '../api.js';
import { Keypad } from '../components/keypad.js';
import { getRoundCards, getTrump } from '../components/game-utils.js';
import { soundScoreRound, soundEndGame } from '../components/sounds.js';

export const roundendScreen = {
    async mount(container, state, { navigate, params }) {
        const gameId = params[0];
        const game = await guardPhase(gameId, 'round_end');
        if (!game) return;
        state.game = game;

        const players = game.players;
        const rps = game.settings.rounds_per_set || 8;
        // Hands entry order: start from player after dealer, same as bidding
        const entryOrder = [];
        for (let i = 1; i <= players.length; i++) {
            entryOrder.push((game.dealer_index + i) % players.length);
        }
        let entryPosition = 0;
        let handsCollected = {};

        document.body.setAttribute('data-phase', 'roundend');

        function currentPlayer() { return entryOrder[entryPosition]; }

        const trumpInfo = getTrump(game.current_round);
        const mode = game.settings.mode || 'expert';

        function getRemainingCards() {
            const cardsDealt = getRoundCards(game.current_round, rps);
            const totalHands = Object.values(handsCollected).reduce((s, v) => s + v, 0);
            return Math.max(0, cardsDealt - totalHands);
        }

        function getDisabledKeys() {
            const isLastPlayer = entryPosition === players.length - 1;
            if (!isLastPlayer) return [];
            // Last player must take exactly the remaining cards
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

            const dealerName = players[game.dealer_index];
            container.innerHTML = `
                <div class="roundend">
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
                    <div class="bid-player-name">${players[pi]}</div>
                    <p class="bid-prompt">How many hands did they make?</p>
                    <p class="claimed-info">${totalHands} of ${cardsDealt} hands accounted${isLastPlayer ? ` — must be ${cardsDealt - totalHands}` : ''}</p>
                    <div id="keypad-container"></div>
                    ${mode !== 'expert' ? `<div class="trump-below ${trumpInfo.isRed ? 'trump-red' : ''}"><span class="trump-symbol-sm">${trumpInfo.symbol}</span><span class="trump-label">${trumpInfo.name}</span></div>` : ''}
                    ${entryPosition > 0 ? '<button id="go-back" class="btn btn-back">← Previous Player</button>' : ''}
                    <p class="error hidden" id="hands-error"></p>
                </div>
            `;

            const keypad = Keypad({
                max: getRemainingCards(),
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

            container.querySelector('#end-game-btn').addEventListener('click', async () => {
                if (confirm('End this game? Scores so far will be saved.')) {
                    await endGame(gameId);
                    soundEndGame();
                    navigate(`scoreboard/${gameId}`);
                }
            });
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
