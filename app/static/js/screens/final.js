// Final screen — game over standings

import { getGame, getScoreboard } from '../api.js';

export const finalScreen = {
    async mount(container, state, { navigate, params }) {
        const gameId = params[0];
        const game = await getGame(gameId);
        const scoreboard = await getScoreboard(gameId);

        const players = game.players;
        const totals = scoreboard.totals;

        document.body.setAttribute('data-phase', 'home');

        // Sort players by score descending
        const standings = players.map((name, index) => ({
            name,
            score: totals[String(index)] || 0,
        })).sort((a, b) => b.score - a.score);

        const winner = standings[0];

        container.innerHTML = `
            <div class="final">
                <div class="final-trophy">🏆</div>
                <h2 class="final-winner">${winner.name}</h2>
                <p class="final-score">${winner.score} points</p>

                <div class="final-standings">
                    ${standings.map((player, rank) => `
                        <div class="final-row ${rank === 0 ? 'final-first' : ''}">
                            <span class="final-rank">${rank + 1}</span>
                            <span class="final-name">${player.name}</span>
                            <span class="final-pts">${player.score}</span>
                        </div>
                    `).join('')}
                </div>

                <div class="final-actions">
                    <button onclick="location.hash=''" class="btn btn-primary">Home</button>
                </div>
            </div>
        `;
    },

    unmount() {},
};
