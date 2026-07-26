// Scoreboard screen — cumulative scores, next round / end game

import { getGame, getScoreboard, undoRound, endGame, nextRound } from '../api.js';

export const scoreboardScreen = {
    async mount(container, state, { navigate, params }) {
        const gameId = params[0];
        const game = await getGame(gameId);
        state.game = game;

        const scoreboard = await getScoreboard(gameId);
        const players = game.players;
        const totals = scoreboard.totals;
        const rounds = scoreboard.rounds;
        const lastRound = rounds.length > 0 ? rounds[rounds.length - 1] : null;

        // Check if at set boundary (every 8 rounds)
        const isSetEnd = game.current_round > 1 && (game.current_round - 1) % 8 === 0;
        const isGameOver = game.status === 'finished';

        document.body.setAttribute('data-phase', 'scoreboard');

        container.innerHTML = `
            <div class="scoreboard">
                <div class="round-info">
                    <span>${isGameOver ? 'Game Over' : `After Round ${game.current_round - 1}`}</span>
                    ${state.playground ? `<span class="share-code-mini">${state.playground.share_code}</span>` : ''}
                    <button class="btn-refresh" onclick="window.dispatchEvent(new HashChangeEvent('hashchange'))">↻</button>
                </div>

                ${lastRound ? `
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
                ` : ''}

                <div class="scoreboard-actions">
                    ${!isGameOver ? `
                        <button id="next-round" class="btn btn-primary">
                            ${isSetEnd ? 'Continue (Next Set)' : 'Next Round'}
                        </button>
                        <button id="end-game" class="btn-text" style="margin-top: 32px; color: var(--danger);">End Game</button>
                        <button id="undo-round" class="btn-text">Undo Last Round</button>
                    ` : `
                        <button onclick="location.hash=''" class="btn btn-primary">Home</button>
                    `}
                </div>
                <p id="scoreboard-error" class="error hidden"></p>
            </div>
        `;

        if (!isGameOver) {
            container.querySelector('#next-round').addEventListener('click', async () => {
                try {
                    await nextRound(gameId);
                    navigate(`bid/${gameId}`);
                } catch (error) {
                    showError(error.message);
                }
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
