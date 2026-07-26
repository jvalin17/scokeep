// Scoreboard screen — cumulative scores, next round / end game

import { getGame, getScoreboard, undoRound, endGame } from '../api.js';

export const scoreboardScreen = {
    async mount(container, state, { navigate, params }) {
        const gameId = params[0];
        const game = await getGame(gameId);
        state.game = game;

        const scoreboard = await getScoreboard(gameId);
        const players = game.players;
        const totals = scoreboard.totals;
        const rounds = scoreboard.rounds;

        // Find leader
        let maxScore = -Infinity;
        let leaderIndex = '0';
        for (const [key, val] of Object.entries(totals)) {
            if (val > maxScore) {
                maxScore = val;
                leaderIndex = key;
            }
        }

        // Check if at set boundary (every 8 rounds)
        const isSetEnd = game.current_round > 1 && (game.current_round - 1) % 8 === 0;
        const isGameOver = game.status === 'finished';

        document.body.setAttribute('data-phase', 'home');

        container.innerHTML = `
            <div class="scoreboard">
                <div class="round-info">
                    <span>${isGameOver ? 'Game Over' : `After Round ${game.current_round - 1}`}</span>
                    ${state.playground ? `<span class="share-code-mini">${state.playground.share_code}</span>` : ''}
                </div>

                <div class="score-table">
                    <div class="score-header">
                        <span>Player</span>
                        <span>Score</span>
                    </div>
                    ${players.map((name, index) => {
                        const key = String(index);
                        const score = totals[key] || 0;
                        const isLeader = key === leaderIndex;
                        return `
                            <div class="score-row ${isLeader ? 'score-leader' : ''}">
                                <span>${name} ${isLeader ? '👑' : ''}</span>
                                <span class="score-value">${score}</span>
                            </div>
                        `;
                    }).join('')}
                </div>

                ${rounds.length > 0 ? `
                    <details class="round-history">
                        <summary>Round History</summary>
                        <div class="history-table">
                            <div class="history-header">
                                <span>Rnd</span>
                                ${players.map(name => `<span>${name.slice(0, 4)}</span>`).join('')}
                            </div>
                            ${rounds.map(round => `
                                <div class="history-row">
                                    <span>${round.round_num}</span>
                                    ${players.map((_, index) => {
                                        const score = round.scores[String(index)] || 0;
                                        return `<span class="${score < 0 ? 'score-negative' : ''}">${score > 0 ? '+' : ''}${score}</span>`;
                                    }).join('')}
                                </div>
                            `).join('')}
                        </div>
                    </details>
                ` : ''}

                <div class="scoreboard-actions">
                    ${!isGameOver ? `
                        <button id="next-round" class="btn btn-primary">
                            ${isSetEnd ? 'Continue (Next Set)' : 'Next Round'}
                        </button>
                        <button id="end-game" class="btn btn-danger">End Game</button>
                        <button id="undo-round" class="btn">Undo Last Round</button>
                    ` : `
                        <button onclick="location.hash=''" class="btn btn-primary">Home</button>
                    `}
                </div>
                <p id="scoreboard-error" class="error hidden"></p>
            </div>
        `;

        if (!isGameOver) {
            container.querySelector('#next-round').addEventListener('click', () => {
                navigate(`bid/${gameId}`);
            });

            container.querySelector('#end-game').addEventListener('click', async () => {
                if (confirm('End this game?')) {
                    try {
                        await endGame(gameId);
                        navigate(`final/${gameId}`);
                    } catch (error) {
                        showError(error.message);
                    }
                }
            });

            container.querySelector('#undo-round').addEventListener('click', async () => {
                try {
                    await undoRound(gameId);
                    // Re-render scoreboard
                    navigate(`scoreboard/${gameId}`);
                    // Force re-render since hash didn't change
                    window.dispatchEvent(new HashChangeEvent('hashchange'));
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
