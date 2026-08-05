// Scoreboard screen — cumulative scores, next round / end game

import { getGame, getScoreboard, undoRound, endGame, nextRound } from '../api.js';
import { getTrump } from '../components/game-utils.js';
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

        // current_round = round just completed (not yet advanced by next-round)
        const roundsPerSet = game.settings.rounds_per_set || 8;
        const isSetEnd = game.current_round % roundsPerSet === 0;
        const isLastRound = game.current_round >= game.total_rounds;
        const isGameOver = game.status === 'finished';

        const appearance = game.settings.appearance || 'standard';
        document.body.setAttribute('data-phase', 'scoreboard');
        document.body.setAttribute('data-appearance', appearance);

        // Build score display
        let scoreTableHtml = '';
        let winnerHtml = '';
        if (rounds.length === 0 && isGameOver) {
            scoreTableHtml = `<p style="text-align:center;color:var(--text-muted);padding:24px 0;">No rounds played</p>`;
        } else if (rounds.length > 0 && isGameOver) {
            // Winner celebration
            const standings = players.map((name, index) => ({
                name, score: totals[String(index)] || 0,
            })).sort((a, b) => b.score - a.score);
            const winner = standings[0];
            // Confetti particles
            const confettiPieces = Array.from({ length: 40 }, (_, i) => {
                const left = Math.random() * 100;
                const delay = Math.random() * 2;
                const duration = 2 + Math.random() * 2;
                const colors = ['#FFD700', '#FF6B6B', '#4ECDC4', '#45B7D1', '#F7DC6F', '#BB8FCE', '#FF9FF3'];
                const color = colors[i % colors.length];
                const size = 6 + Math.random() * 6;
                return `<div class="confetti-piece" style="left:${left}%;animation-delay:${delay}s;animation-duration:${duration}s;background:${color};width:${size}px;height:${size}px;"></div>`;
            }).join('');

            // Rankings
            const rankEmojis = ['🥇', '🥈', '🥉'];
            const rankingsHtml = `
                <div class="final-rankings">
                    ${standings.map((player, rank) => `
                        <div class="rank-row ${rank === 0 ? 'rank-first' : ''}">
                            <span class="rank-badge">${rankEmojis[rank] || rank + 1}</span>
                            <span class="rank-name">${player.name}</span>
                            <span class="rank-score">${player.score}</span>
                        </div>
                    `).join('')}
                </div>
            `;

            winnerHtml = `
                <div class="final-celebration">
                    <div class="confetti-container">${confettiPieces}</div>
                    <div class="final-trophy">🏆</div>
                    <h2 class="final-winner">${winner.name}</h2>
                    <p class="final-score">${winner.score} points</p>
                </div>
            `;

            // Game over: full scoresheet — round scores only, total at bottom
            scoreTableHtml = `
                <div class="score-table score-table-full">
                    <table class="scoresheet">
                        <thead>
                            <tr>
                                <th>R#</th>
                                <th>Trump</th>
                                ${players.map(name => `<th>${name}</th>`).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${rounds.map(round => {
                                const trump = getTrump(round.round_num);
                                return `<tr>
                                    <td>${round.round_num}</td>
                                    <td class="${trump.isRed ? 'trump-red' : ''}">${trump.symbol}</td>
                                    ${players.map((_, idx) => {
                                        const roundScore = round.scores[String(idx)] || 0;
                                        return `<td class="${roundScore < 0 ? 'score-negative' : ''}">
                                            ${roundScore > 0 ? '+' : ''}${roundScore}
                                        </td>`;
                                    }).join('')}
                                </tr>`;
                            }).join('')}
                        </tbody>
                        <tfoot>
                            <tr class="totals-row">
                                <td><strong>Tot</strong></td>
                                <td></td>
                                ${players.map((_, idx) => `<td><strong>${totals[String(idx)] || 0}</strong></td>`).join('')}
                            </tr>
                        </tfoot>
                    </table>
                </div>
                ${rankingsHtml}
            `;
        } else if (rounds.length > 0) {
            // Between rounds: round score only — no grand total
            const lastRound = rounds[rounds.length - 1];
            scoreTableHtml = `
                <div class="score-table">
                    <div class="score-header">
                        <span>Player</span>
                        <span>Round ${lastRound.round_num}</span>
                    </div>
                    ${players.map((name, index) => {
                        const key = String(index);
                        const score = lastRound.scores[key] || 0;
                        return `
                            <div class="score-row">
                                <span>${name}</span>
                                <span class="score-value ${score < 0 ? 'score-negative' : ''}">${score > 0 ? '+' : ''}${score}</span>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        }

        container.innerHTML = `
            <div class="scoreboard">
                ${isGameOver ? winnerHtml : `
                    <div class="round-info">
                        <span>After Round ${game.current_round}</span>
                        ${state.playground ? `<button class="btn-home" onclick="location.hash='playground/${state.playground.share_code}'">🏠</button>` : ''}
                    </div>
                `}

                ${scoreTableHtml}

                <div class="scoreboard-actions">
                    ${isGameOver ? `
                        <button onclick="location.hash='${state.playground ? `playground/${state.playground.share_code}` : ''}'" class="btn btn-primary">🏠 Back to Room</button>
                    ` : `
                        <button id="next-round" class="btn btn-primary">${isLastRound ? 'Finish Game' : 'Next Round'}</button>
                        <button id="end-game" class="btn-text" style="margin-top: 32px; color: var(--danger);">End Game</button>
                        <button id="undo-round" class="btn-text">Undo Last Round</button>
                    `}
                </div>
                <p id="scoreboard-error" class="error hidden"></p>
            </div>
        `;

        if (!isGameOver) {
            const nextRoundBtn = container.querySelector('#next-round');
            if (nextRoundBtn) {
                nextRoundBtn.addEventListener('click', async () => {
                    try {
                        const updated = await nextRound(gameId);
                        if (updated.status === 'finished') {
                            navigate(`scoreboard/${gameId}`);
                            window.dispatchEvent(new HashChangeEvent('hashchange'));
                        } else {
                            soundNextRound();
                            navigate(`bid/${gameId}`);
                        }
                    } catch (error) {
                        showError(error.message);
                    }
                });
            }

            const endGameBtn = container.querySelector('#end-game');
            if (endGameBtn) {
                endGameBtn.addEventListener('click', async () => {
                    try {
                        await endGame(gameId);
                        soundEndGame();
                        navigate(`scoreboard/${gameId}`);
                        window.dispatchEvent(new HashChangeEvent('hashchange'));
                    } catch (error) {
                        showError(error.message);
                    }
                });
            }

            const undoBtn = container.querySelector('#undo-round');
            if (undoBtn) {
                undoBtn.addEventListener('click', async () => {
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
        }

        function showError(message) {
            const errorEl = container.querySelector('#scoreboard-error');
            if (!errorEl) return;
            errorEl.textContent = message;
            errorEl.classList.remove('hidden');
        }
    },

    unmount() {},
};
