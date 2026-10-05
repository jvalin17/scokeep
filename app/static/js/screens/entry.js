// Scoresheet entry — dialer buffer + Next (no network on keypress).

import { getApi } from '../resolve-api.js';
import { escapeHtml } from '../components/game-utils.js';
import { getEntryOrder } from '../components/entry-utils.js';
import {
    renderGameIsland,
    renderRoundInfoBar,
    attachEndGameHandler,
    showError,
    setScreenContext,
} from '../components/screen-parts.js';
import {
    createDialerState,
    pushDigit,
    backspace,
    toggleSign,
    clearBuffer,
    displayValue,
    canCommit,
    parsedScore,
    canAcceptNext,
} from '../components/score-dialer.js';
import { ScoreDialerKeypad } from '../components/score-dialer-keypad.js';

export const entryScreen = {
    async mount(container, state, { navigate, params }) {
        const gameId = params[0];
        const api = await getApi(gameId);
        const game = await api.guardPhase(gameId, 'entry');
        if (!game) return;
        state.game = game;

        const players = game.players;
        const settings = game.settings || {};
        const allowNegatives = settings.allow_negatives === true;
        const label = (settings.label || '').trim();
        const entryOrder = getEntryOrder(game.dealer_index || 0, players.length);

        let position = 0;
        /** @type {Record<string, number>} */
        let scoresCollected = {};
        let dialer = createDialerState({ allowNegatives, maxDigits: 4 });
        let lastCommitAt = 0;
        let flashMessage = '';

        setScreenContext('entry', game);
        document.body.setAttribute('data-phase', 'entry');

        function currentPlayerIndex() {
            return entryOrder[position];
        }

        function showFlash(message) {
            flashMessage = message;
            const flashEl = container.querySelector('#dialer-flash');
            if (flashEl) {
                flashEl.textContent = message;
                flashEl.classList.toggle('hidden', !message);
            }
        }

        function renderReview() {
            const rows = entryOrder
                .map((playerIndex) => {
                    const name = players[playerIndex];
                    const score = scoresCollected[String(playerIndex)];
                    return `
                        <div class="confirm-row" data-player-index="${playerIndex}">
                            <span class="confirm-name">${escapeHtml(name)}</span>
                            <span class="confirm-value">${score}</span>
                            <button type="button" class="btn-small" data-edit="${playerIndex}">Edit</button>
                        </div>`;
                })
                .join('');

            container.innerHTML = `
                <div class="game-screen scoresheet-entry">
                    ${renderGameIsland(game, settings.rounds_per_set || 8)}
                    ${renderRoundInfoBar(state)}
                    <div class="round-info"><span>${escapeHtml(label || 'Scoresheet')}</span></div>
                    <div id="scoresheet-review" class="scoresheet-review" data-scoresheet-review="1">
                        <h3>Round review</h3>
                        ${rows}
                    </div>
                    <button type="button" class="btn btn-primary btn-large" id="btn-score-round">Score Round</button>
                    <p class="error hidden" id="entry-error"></p>
                </div>
            `;

            container.querySelectorAll('[data-edit]').forEach((btn) => {
                btn.addEventListener('click', () => {
                    const playerIndex = parseInt(btn.getAttribute('data-edit'), 10);
                    position = entryOrder.indexOf(playerIndex);
                    delete scoresCollected[String(playerIndex)];
                    dialer = createDialerState({ allowNegatives, maxDigits: 4 });
                    renderCollecting();
                });
            });

            container.querySelector('#btn-score-round').addEventListener('click', async () => {
                const btn = container.querySelector('#btn-score-round');
                if (btn) btn.disabled = true;
                try {
                    await api.lockScoresheetRound(gameId, scoresCollected);
                    const updated = await api.getGame(gameId);
                    state.game = updated;
                    const route =
                        updated.phase === 'intermission' ? 'scoreboard' : 'scoreboard';
                    navigate(`${route}/${gameId}`);
                } catch (err) {
                    if (btn) btn.disabled = false;
                    showError(container, 'entry-error', err.message || String(err));
                }
            });

            attachEndGameHandler(container, game, navigate);
        }

        function renderCollecting() {
            if (position >= players.length) {
                renderReview();
                return;
            }

            const playerIndex = currentPlayerIndex();
            const playerName = players[playerIndex];
            const entered = Object.keys(scoresCollected).length;

            container.innerHTML = `
                <div class="game-screen scoresheet-entry">
                    ${renderGameIsland(game, settings.rounds_per_set || 8)}
                    ${renderRoundInfoBar(state)}
                    <div class="round-info"><span>${escapeHtml(label || 'Scoresheet')}</span></div>
                    <div class="bid-player-name" data-entry-player="${playerIndex}">${escapeHtml(playerName)}</div>
                    <p class="bid-prompt">Enter score</p>
                    <div id="score-display" class="score-display" data-dialer-display="1" aria-live="polite">${escapeHtml(displayValue(dialer))}</div>
                    <p id="dialer-flash" class="claimed-info ${flashMessage ? '' : 'hidden'}">${escapeHtml(flashMessage)}</p>
                    <p class="claimed-info">${entered} / ${players.length} entered</p>
                    <div id="keypad-container"></div>
                    <div class="bid-nav">
                        <button type="button" class="btn btn-primary" id="btn-next">Next</button>
                    </div>
                    <p class="error hidden" id="entry-error"></p>
                </div>
            `;

            const keypadHost = container.querySelector('#keypad-container');
            keypadHost.appendChild(
                ScoreDialerKeypad({
                    allowNegatives,
                    onDigit: (digit) => {
                        dialer = pushDigit(dialer, digit);
                        if (dialer.flash === 'max_digits') {
                            showFlash('Max 4 digits');
                        } else {
                            showFlash('');
                        }
                        const display = container.querySelector('#score-display');
                        if (display) display.textContent = displayValue(dialer);
                    },
                    onBackspace: () => {
                        dialer = backspace(dialer);
                        showFlash('');
                        const display = container.querySelector('#score-display');
                        if (display) display.textContent = displayValue(dialer);
                    },
                    onClear: () => {
                        dialer = clearBuffer(dialer);
                        showFlash('');
                        const display = container.querySelector('#score-display');
                        if (display) display.textContent = displayValue(dialer);
                    },
                    onSign: () => {
                        dialer = toggleSign(dialer);
                        const display = container.querySelector('#score-display');
                        if (display) display.textContent = displayValue(dialer);
                    },
                }),
            );

            container.querySelector('#btn-next').addEventListener('click', () => {
                const now = Date.now();
                if (!canAcceptNext(lastCommitAt, now)) {
                    showFlash('Wait a moment');
                    return;
                }
                if (!canCommit(dialer)) {
                    showFlash('Enter a score first');
                    return;
                }
                const score = parsedScore(dialer);
                if (score === null) {
                    showFlash('Enter a score first');
                    return;
                }
                scoresCollected[String(playerIndex)] = score;
                lastCommitAt = now; // block double-tap until re-render
                dialer = createDialerState({ allowNegatives, maxDigits: 4 });
                flashMessage = '';
                position += 1;
                lastCommitAt = 0; // next player can Next immediately after digits
                renderCollecting();
            });

            attachEndGameHandler(container, game, navigate);
        }

        renderCollecting();
    },
};
