// Review screen — edit any round's scores before finalizing

import { getGame, getScoreboard, confirmFinal, rescoreRound, submitHands, endRound, guardPhase } from '../api.js';
import { escapeHtml } from '../components/game-utils.js';
import { InlineKeypad } from '../components/keypad.js';
import { renderScoresheetTable } from '../components/screen-parts.js';
import { soundEndGame } from '../components/sounds.js';

export const reviewScreen = {
    async mount(container, state, { navigate, params }) {
        const gameId = params[0];
        const game = await guardPhase(gameId, 'review');
        if (!game) return;
        state.game = game;

        const scoreboard = await getScoreboard(gameId);
        const players = game.players;
        const totals = scoreboard.totals;
        const rounds = scoreboard.rounds;

        let editingRoundNum = null;
        let editingPlayerIndex = null;
        let editingHands = {};

        document.body.setAttribute('data-phase', 'review');
        document.body.setAttribute('data-appearance', game.settings.appearance || 'standard');

        async function finalizeGame() {
            try {
                await confirmFinal(gameId);
                soundEndGame();
                navigate(`scoreboard/${gameId}`);
            } catch (error) {
                showError(error.message);
            }
        }

        function renderReview() {
            const standings = players.map((name, index) => ({
                name, score: totals[String(index)] || 0,
            })).sort((a, b) => b.score - a.score);

            container.innerHTML = `
                <div class="review-screen">
                    <div class="round-info">
                        <span>Review Scores</span>
                    </div>
                    <p class="review-hint">Tap any round to edit hands before finalizing.</p>

                    ${renderScoresheetTable(players, rounds, totals, {
                        rowAttrs: (round) => `class="review-round-row ${editingRoundNum === round.round_num ? 'review-editing' : ''}" data-round="${round.round_num}"`
                    })}

                    <div id="edit-area"></div>

                    <div class="scoreboard-actions">
                        <button id="confirm-final" class="btn btn-primary">Confirm Final Scores</button>
                        <button id="skip-review" class="btn-text" style="margin-top: 12px;">Skip Review</button>
                    </div>
                    <p id="review-error" class="error hidden"></p>
                </div>
            `;

            container.querySelectorAll('.review-round-row').forEach(row => {
                row.addEventListener('click', () => {
                    const roundNum = parseInt(row.dataset.round);
                    if (editingRoundNum === roundNum) {
                        editingRoundNum = null;
                        editingPlayerIndex = null;
                        editingHands = {};
                        renderReview();
                    } else {
                        startEditingRound(roundNum);
                    }
                });
            });

            if (editingRoundNum !== null) {
                renderEditArea();
            }

            container.querySelector('#confirm-final').addEventListener('click', finalizeGame);
            container.querySelector('#skip-review').addEventListener('click', finalizeGame);
        }

        async function startEditingRound(roundNum) {
            try {
                await rescoreRound(gameId, roundNum);
                // Load the round's existing hands
                const roundData = rounds.find(r => r.round_num === roundNum);
                editingRoundNum = roundNum;
                editingPlayerIndex = null;
                editingHands = roundData ? { ...roundData.hands_won } : {};
                renderReview();
            } catch (error) {
                showError(error.message);
            }
        }

        function renderEditArea() {
            const editArea = container.querySelector('#edit-area');
            if (!editArea) return;

            const roundData = rounds.find(r => r.round_num === editingRoundNum);
            const cardsDealt = roundData ? roundData.cards_dealt : 0;
            const totalHands = Object.values(editingHands).reduce((sum, v) => sum + v, 0);

            editArea.innerHTML = `
                <div class="review-edit-panel">
                    <h3>Edit Round ${editingRoundNum} Hands</h3>
                    <div class="bid-summary">
                        ${players.map((name, idx) => {
                            const key = String(idx);
                            const isEditing = editingPlayerIndex === idx;
                            return `
                                <div class="bid-summary-row">
                                    <span>${escapeHtml(name)}</span>
                                    <span class="bid-summary-value">${editingHands[key] ?? '?'}</span>
                                    <button class="btn-small btn-edit" data-edit-player="${idx}">${isEditing ? 'Cancel' : 'Edit'}</button>
                                </div>
                                ${isEditing ? '<div id="review-inline-keypad"></div>' : ''}
                            `;
                        }).join('')}
                    </div>
                    <div class="bid-total">
                        Total: ${totalHands} / ${cardsDealt} ${totalHands === cardsDealt ? '\u2713' : '\u26A0'}
                    </div>
                    ${totalHands === cardsDealt ? '<button id="rescore-confirm" class="btn btn-primary">Re-Score Round</button>' : '<p class="claimed-info">Total must equal cards dealt</p>'}
                    <button id="cancel-edit" class="btn-text" style="margin-top: 8px;">Cancel Edit</button>
                    <p id="edit-error" class="error hidden"></p>
                </div>
            `;

            editArea.querySelectorAll('[data-edit-player]').forEach(btn => {
                btn.addEventListener('click', (event) => {
                    event.stopPropagation();
                    const playerIdx = parseInt(btn.dataset.editPlayer);
                    editingPlayerIndex = (editingPlayerIndex === playerIdx) ? null : playerIdx;
                    renderEditArea();
                });
            });

            const keypadSlot = editArea.querySelector('#review-inline-keypad');
            if (keypadSlot && editingPlayerIndex !== null) {
                const editKey = String(editingPlayerIndex);
                const othersTotal = Object.entries(editingHands)
                    .filter(([k]) => k !== editKey)
                    .reduce((sum, [, v]) => sum + v, 0);
                const maxForPlayer = Math.max(0, cardsDealt - othersTotal);

                const inlineKeypad = InlineKeypad({
                    max: maxForPlayer,
                    disabled: [],
                    onSelect: async (value) => {
                        try {
                            await submitHands(gameId, editingPlayerIndex, value);
                            editingHands[editKey] = value;

                            // Auto-adjust last player if needed
                            const lastPlayerIdx = players.length - 1;
                            if (editingPlayerIndex !== lastPlayerIdx) {
                                const newOthersTotal = Object.entries(editingHands)
                                    .filter(([k]) => k !== String(lastPlayerIdx))
                                    .reduce((sum, [, v]) => sum + v, 0);
                                const lastValue = cardsDealt - newOthersTotal;
                                if (lastValue >= 0 && Object.keys(editingHands).length === players.length) {
                                    await submitHands(gameId, lastPlayerIdx, lastValue);
                                    editingHands[String(lastPlayerIdx)] = lastValue;
                                }
                            }

                            editingPlayerIndex = null;
                            renderEditArea();
                        } catch (error) {
                            const errEl = editArea.querySelector('#edit-error');
                            if (errEl) {
                                errEl.textContent = error.message;
                                errEl.classList.remove('hidden');
                            }
                        }
                    },
                });
                keypadSlot.appendChild(inlineKeypad);
            }

            const rescoreBtn = editArea.querySelector('#rescore-confirm');
            if (rescoreBtn) {
                rescoreBtn.addEventListener('click', async () => {
                    try {
                        await endRound(gameId);
                        // Refresh scoreboard data
                        const updatedScoreboard = await getScoreboard(gameId);
                        rounds.length = 0;
                        rounds.push(...updatedScoreboard.rounds);
                        Object.assign(totals, updatedScoreboard.totals);
                        editingRoundNum = null;
                        editingPlayerIndex = null;
                        editingHands = {};
                        renderReview();
                    } catch (error) {
                        const errEl = editArea.querySelector('#edit-error');
                        if (errEl) {
                            errEl.textContent = error.message;
                            errEl.classList.remove('hidden');
                        }
                    }
                });
            }

            const cancelBtn = editArea.querySelector('#cancel-edit');
            if (cancelBtn) {
                cancelBtn.addEventListener('click', async () => {
                    try {
                        await endRound(gameId);
                    } catch { /* ignore — may already be scored */ }
                    editingRoundNum = null;
                    editingPlayerIndex = null;
                    editingHands = {};
                    renderReview();
                });
            }
        }

        function showError(message) {
            const errorEl = container.querySelector('#review-error');
            if (!errorEl) return;
            errorEl.textContent = message;
            errorEl.classList.remove('hidden');
        }

        renderReview();
    },

    unmount() {},
};
