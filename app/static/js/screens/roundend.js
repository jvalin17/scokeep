// Round end screen — hands won entry via keypad + back button

import { submitHands, endRound, extendGame, nextRound, resyncGame, guardPhase, getBids } from '../api.js';
import { Keypad, InlineKeypad } from '../components/keypad.js';
import { getRoundCards, escapeHtml } from '../components/game-utils.js';
import { getEntryOrder } from '../components/entry-utils.js';
import { renderGameIsland, renderRoundInfoBar, renderTrumpDisplay, attachEndGameHandler, showError, setScreenContext } from '../components/screen-parts.js';
import { soundScoreRound, soundNextRound } from '../components/sounds.js';


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
        let editingPi = null;

        setScreenContext('roundend', game);

        // Rescore mode: load existing hands and skip to confirm
        if (state.rescore) {
            try {
                const roundData = await getBids(gameId);
                const existingHands = roundData.hands_won || {};
                for (const [key, value] of Object.entries(existingHands)) {
                    handsCollected[key] = value;
                }
                entryPosition = players.length; // skip sequential entry
            } catch { /* fall through to normal entry */ }
        }

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
                    <div class="bid-player-name">${escapeHtml(players[pi])}</div>
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
                onSelect: (value) => {
                    handleHandsSelect(value);
                },
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

            attachEndGameHandler(container, gameId, navigate, state);
        }

        function renderConfirm() {
            const cardsDealt = getRoundCards(game.current_round, rps);
            const totalHands = Object.values(handsCollected).reduce((sum, v) => sum + v, 0);
            const lastPi = entryOrder[entryOrder.length - 1];

            container.innerHTML = `
                <div class="roundend">
                    <div class="round-info">
                        <span>Round ${game.current_round}</span>
                    </div>
                    <h3>Confirm Hands Won</h3>
                    <div class="bid-summary">
                        ${entryOrder.map(pi => {
                            const key = String(pi);
                            const isEditing = editingPi === pi;
                            return `
                                <div class="bid-summary-row">
                                    <span>${escapeHtml(players[pi])}${pi === game.dealer_index ? ' (D)' : ''}</span>
                                    <span class="bid-summary-value">${handsCollected[key] ?? '?'}</span>
                                    <button class="btn-small btn-edit" data-edit="${pi}">${isEditing ? 'Cancel' : 'Edit'}</button>
                                </div>
                                ${isEditing ? '<div id="inline-keypad-slot"></div>' : ''}
                            `;
                        }).join('')}
                    </div>
                    <div class="bid-total">
                        Total: ${totalHands} / ${cardsDealt} ${totalHands === cardsDealt ? '✓' : '⚠'}
                    </div>
                    ${totalHands === cardsDealt ? `<button id="score-round" class="btn btn-primary">${state.rescore ? 'Re-Score Round' : 'Score Round'}</button>` : '<p class="claimed-info">Total must equal cards dealt</p>'}
                    <p id="score-error" class="error hidden"></p>
                </div>
            `;

            // Edit button toggles inline keypad
            container.querySelectorAll('[data-edit]').forEach(btn => {
                btn.addEventListener('click', () => {
                    const pi = parseInt(btn.dataset.edit);
                    editingPi = (editingPi === pi) ? null : pi;
                    renderConfirm();
                });
            });

            // Mount inline keypad if editing
            const keypadSlot = container.querySelector('#inline-keypad-slot');
            if (keypadSlot && editingPi !== null) {
                const editKey = String(editingPi);
                const othersTotal = Object.entries(handsCollected)
                    .filter(([k]) => k !== editKey)
                    .reduce((sum, [, v]) => sum + v, 0);
                const maxForThisPlayer = cardsDealt - othersTotal;

                const inlineKeypad = InlineKeypad({
                    max: Math.max(0, maxForThisPlayer),
                    disabled: [],
                    onSelect: async (value) => {
                        try {
                            await submitHands(gameId, editingPi, value);
                            handsCollected[editKey] = value;

                            // Auto-adjust last player to keep total = cards dealt
                            if (editingPi !== lastPi) {
                                const newOthersTotal = Object.entries(handsCollected)
                                    .filter(([k]) => k !== String(lastPi))
                                    .reduce((sum, [, v]) => sum + v, 0);
                                const lastValue = cardsDealt - newOthersTotal;
                                if (lastValue >= 0) {
                                    await submitHands(gameId, lastPi, lastValue);
                                    handsCollected[String(lastPi)] = lastValue;
                                }
                            }

                            editingPi = null;
                            renderConfirm();
                        } catch (error) {
                            showError(container, 'score-error', error.message);
                        }
                    },
                });
                keypadSlot.appendChild(inlineKeypad);
            }

            const scoreBtn = container.querySelector('#score-round');
            if (scoreBtn) {
                scoreBtn.addEventListener('click', async () => {
                    try {
                        await endRound(gameId);
                        soundScoreRound();
                        state.rescore = false;
                        const isFinalRound = game.current_round >= game.total_rounds;
                        if (isFinalRound) {
                            renderExtendPrompt();
                        } else {
                            navigate(`scoreboard/${gameId}`);
                        }
                    } catch {
                        await resyncGame(gameId);
                    }
                });
            }
        }

        function renderExtendPrompt() {
            const rps = game.settings.rounds_per_set || 8;
            container.innerHTML = `
                <div class="roundend">
                    <div class="round-info">
                        <span>Set Complete!</span>
                    </div>
                    <h3>All ${game.total_rounds} rounds played</h3>
                    <div class="scoreboard-actions">
                        <div style="display:flex;gap:8px;align-items:center;justify-content:center;margin-bottom:12px;">
                            <label>Add</label>
                            <select id="extend-count">
                                ${[1,2,3,4].map(n => `<option value="${n}">${n} set${n > 1 ? 's' : ''} (${n * rps} rounds)</option>`).join('')}
                            </select>
                        </div>
                        <button id="extend-set" class="btn btn-primary">Add & Continue</button>
                        <button id="see-scores" class="btn" style="margin-top: 12px;">See Scores</button>
                    </div>
                </div>
            `;

            container.querySelector('#extend-set').addEventListener('click', async () => {
                const count = parseInt(container.querySelector('#extend-count').value);
                try {
                    for (let i = 0; i < count; i++) {
                        await extendGame(gameId);
                    }
                    await nextRound(gameId);
                    soundNextRound();
                    navigate(`bid/${gameId}`);
                } catch {
                    navigate(`scoreboard/${gameId}`);
                }
            });

            container.querySelector('#see-scores').addEventListener('click', () => {
                navigate(`scoreboard/${gameId}`);
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
