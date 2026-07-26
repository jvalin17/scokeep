// Scoreboard screen — cumulative scores, next round / end game

import { getGame, getScoreboard, undoRound, endGame, nextRound } from '../api.js';
import { soundNextRound, soundEndGame, soundUndo } from '../components/sounds.js';

export const scoreboardScreen = {
    async mount(container, state, { navigate, params }) {
        const gameId = params[0];
        const game = await getGame(gameId);
        // Scoreboard accepts both 'scoreboard' and 'final' phases
        if (game.phase !== 'scoreboard' && game.status !== 'finished') {
            const { guardPhase: gp } = await import('../api.js');
            await gp(gameId, game.phase); // will redirect
            return;
        }
        state.game = game;

        const scoreboard = await getScoreboard(gameId);
        const players = game.players;
        const totals = scoreboard.totals;
        const rounds = scoreboard.rounds;

        // Check if at set boundary (every 8 rounds)
        const isSetEnd = game.current_round > 1 && (game.current_round - 1) % 8 === 0;
        const isGameOver = game.status === 'finished';

        document.body.setAttribute('data-phase', 'scoreboard');

        // Build cumulative score table
        let scoreTableHtml = '';
        if (rounds.length === 0 && isGameOver) {
            scoreTableHtml = `<p style="text-align:center;color:var(--text-muted);padding:24px 0;">No rounds played</p>`;
        } else if (rounds.length > 0) {
            // Calculate running totals per player per round
            const runningTotals = players.map(() => 0);

            scoreTableHtml = `
                <div class="score-table score-table-full">
                    <table class="scoresheet">
                        <thead>
                            <tr>
                                <th>R#</th>
                                ${players.map(name => `<th>${name}</th>`).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${rounds.map(round => {
                                players.forEach((_, idx) => {
                                    runningTotals[idx] += (round.scores[String(idx)] || 0);
                                });
                                return `<tr>
                                    <td>${round.round_num}</td>
                                    ${players.map((_, idx) => {
                                        const roundScore = round.scores[String(idx)] || 0;
                                        const total = runningTotals[idx];
                                        return `<td class="${roundScore < 0 ? 'score-negative' : ''}">
                                            <span class="round-score">${roundScore > 0 ? '+' : ''}${roundScore}</span>
                                            <span class="running-total">${total}</span>
                                        </td>`;
                                    }).join('')}
                                </tr>`;
                            }).join('')}
                        </tbody>
                        <tfoot>
                            <tr class="totals-row">
                                <td><strong>Total</strong></td>
                                ${players.map((_, idx) => `<td><strong>${totals[String(idx)] || 0}</strong></td>`).join('')}
                            </tr>
                        </tfoot>
                    </table>
                </div>
            `;
        }

        container.innerHTML = `
            <div class="scoreboard">
                <div class="round-info">
                    <span>${isGameOver ? 'Game Over' : `After Round ${game.current_round - 1}`}</span>
                    ${state.playground ? `<button class="btn-home" onclick="location.hash='playground/${state.playground.share_code}'">🏠</button>` : ''}
                </div>

                ${scoreTableHtml}

                <div class="scoreboard-actions">
                    ${!isGameOver ? `
                        <button id="next-round" class="btn btn-primary">
                            ${isSetEnd ? 'Continue (Next Set)' : 'Next Round'}
                        </button>
                        <button id="end-game" class="btn-text" style="margin-top: 32px; color: var(--danger);">End Game</button>
                        <button id="undo-round" class="btn-text">Undo Last Round</button>
                    ` : `
                        <button onclick="location.hash=''" class="btn btn-primary">🏠 Home</button>
                    `}
                </div>
                <p id="scoreboard-error" class="error hidden"></p>
            </div>
        `;

        if (!isGameOver) {
            container.querySelector('#next-round').addEventListener('click', async () => {
                try {
                    await nextRound(gameId);
                    soundNextRound();
                    navigate(`bid/${gameId}`);
                } catch (error) {
                    showError(error.message);
                }
            });

            container.querySelector('#end-game').addEventListener('click', async () => {
                if (confirm('End this game?')) {
                    try {
                        await endGame(gameId);
                        soundEndGame();
                        navigate(`scoreboard/${gameId}`);
                        window.dispatchEvent(new HashChangeEvent('hashchange'));
                    } catch (error) {
                        showError(error.message);
                    }
                }
            });

            container.querySelector('#undo-round').addEventListener('click', async () => {
                try {
                    await undoRound(gameId);
                    soundUndo();
                    const updated = await getGame(gameId);
                    if (updated.phase === 'bidding') {
                        navigate(`bid/${gameId}`);
                    } else {
                        navigate(`scoreboard/${gameId}`);
                        window.dispatchEvent(new HashChangeEvent('hashchange'));
                    }
                } catch (error) {
                    showError(error.message);
                }
            });
        }

        function showError(message) {
            const errorEl = container.querySelector('#scoreboard-error');
            errorEl.textContent = message;
            errorEl.classList.remove('hidden');
        }
    },

    unmount() {},
};
