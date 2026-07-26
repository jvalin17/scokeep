// Free Score screen — enter any score per player, no bids/trump

import { getGame, getScoreboard, endGame, nextRound, submitBid, getBids, startRound, enterRoundEnd, submitHands, endRound } from '../api.js';

export const freescoreScreen = {
    async mount(container, state, { navigate, params }) {
        const gameId = params[0];
        const game = await getGame(gameId);
        state.game = game;

        const players = game.players;
        let scores = {};
        let currentIndex = 0;
        let phase = 'entry'; // entry | review | scoreboard

        document.body.setAttribute('data-phase', 'roundend');

        // Check if round already has data (resuming)
        try {
            const roundData = await getBids(gameId);
            if (roundData.status === 'scored') {
                phase = 'scoreboard';
            }
        } catch (e) { console.warn('No existing round data:', e.message); }

        function renderEntry() {
            phase = 'entry';
            container.innerHTML = `
                <div class="freescore">
                    <div class="round-info">
                        <span>Round ${game.current_round} of ${game.total_rounds}</span>
                        <span>Free Score</span>
                        ${state.playground ? `<span class="share-code-mini">${state.playground.share_code}</span>` : ''}
                    </div>
                    <div class="bid-player-name">${players[currentIndex]}</div>
                    <p class="bid-prompt">Enter score</p>
                    <div class="free-input-row">
                        <button class="free-sign-btn" id="sign-toggle">+</button>
                        <input type="number" id="score-input" class="free-score-input"
                            value="0" min="0" max="999" inputmode="numeric">
                    </div>
                    <button id="submit-score" class="btn btn-primary" style="margin-top: 12px;">Submit</button>
                    ${currentIndex > 0 ? '<button id="go-back" class="btn btn-back">← Previous Player</button>' : ''}
                    <p class="error hidden" id="free-error"></p>
                </div>
            `;

            const input = container.querySelector('#score-input');
            const signBtn = container.querySelector('#sign-toggle');
            let negative = false;

            signBtn.addEventListener('click', () => {
                negative = !negative;
                signBtn.textContent = negative ? '−' : '+';
                signBtn.classList.toggle('free-sign-negative', negative);
            });

            input.addEventListener('focus', () => {
                if (input.value === '0') input.value = '';
            });

            container.querySelector('#submit-score').addEventListener('click', () => {
                const val = parseInt(input.value) || 0;
                scores[String(currentIndex)] = negative ? -val : val;
                currentIndex++;
                if (currentIndex >= players.length) {
                    renderReview();
                } else {
                    renderEntry();
                }
            });

            const backBtn = container.querySelector('#go-back');
            if (backBtn) {
                backBtn.addEventListener('click', () => {
                    currentIndex--;
                    delete scores[String(currentIndex)];
                    renderEntry();
                });
            }
        }

        function renderReview() {
            phase = 'review';
            container.innerHTML = `
                <div class="freescore">
                    <div class="round-info">
                        <span>Round ${game.current_round}</span>
                    </div>
                    <h3>Confirm Scores</h3>
                    <div class="bid-summary">
                        ${players.map((name, i) => `
                            <div class="bid-summary-row">
                                <span>${name}</span>
                                <span class="bid-summary-value ${(scores[String(i)] || 0) < 0 ? 'score-negative' : ''}">
                                    ${(scores[String(i)] || 0) > 0 ? '+' : ''}${scores[String(i)] || 0}
                                </span>
                                <button class="btn-small btn-edit" data-edit="${i}">Edit</button>
                            </div>
                        `).join('')}
                    </div>
                    <button id="save-round" class="btn btn-primary" style="margin-top: 12px;">Save Round</button>
                    <p class="error hidden" id="free-error"></p>
                </div>
            `;

            container.querySelectorAll('[data-edit]').forEach(btn => {
                btn.addEventListener('click', () => {
                    currentIndex = parseInt(btn.dataset.edit);
                    delete scores[String(currentIndex)];
                    renderEntry();
                });
            });

            container.querySelector('#save-round').addEventListener('click', async () => {
                try {
                    // bid = absolute value, hands = bid (positive) or 0 (negative)
                    for (const [idx, score] of Object.entries(scores)) {
                        await submitBid(gameId, parseInt(idx), Math.abs(score));
                    }
                    await startRound(gameId);
                    await enterRoundEnd(gameId);
                    for (const [idx, score] of Object.entries(scores)) {
                        const absVal = Math.abs(score);
                        const hands = score >= 0 ? absVal : absVal + 1;
                        await submitHands(gameId, parseInt(idx), hands);
                    }
                    await endRound(gameId);
                    renderScoreboard();
                } catch (error) {
                    const el = container.querySelector('#free-error');
                    el.textContent = error.message;
                    el.classList.remove('hidden');
                }
            });
        }

        async function renderScoreboard() {
            phase = 'scoreboard';
            const scoreboard = await getScoreboard(gameId);
            const totals = scoreboard.totals;
            const lastRound = scoreboard.rounds.length > 0 ? scoreboard.rounds[scoreboard.rounds.length - 1] : null;
            const isGameOver = game.status === 'finished' || game.current_round >= game.total_rounds;

            // Find leader
            let maxScore = -Infinity;
            let leaderName = '';
            for (const [key, val] of Object.entries(totals)) {
                if (val > maxScore) { maxScore = val; leaderName = players[parseInt(key)]; }
            }

            container.innerHTML = `
                <div class="freescore">
                    <div class="round-info">
                        <span>${isGameOver ? 'Game Over' : `After Round ${scoreboard.rounds.length}`}</span>
                        ${state.playground ? `<span class="share-code-mini">${state.playground.share_code}</span>` : ''}
                    </div>

                    <div class="score-table">
                        <div class="score-header">
                            <span>Player</span>
                            ${lastRound ? '<span>Round</span>' : ''}
                            <span>Total</span>
                        </div>
                        ${players.map((name, i) => {
                            const key = String(i);
                            const total = totals[key] || 0;
                            const roundScore = lastRound ? (lastRound.scores[key] || 0) : null;
                            const isLeader = name === leaderName;
                            return `
                                <div class="score-row ${isLeader ? 'score-leader' : ''}">
                                    <span>${name} ${isLeader ? '👑' : ''}</span>
                                    ${lastRound ? `<span class="${roundScore < 0 ? 'score-negative' : ''}">${roundScore > 0 ? '+' : ''}${roundScore}</span>` : ''}
                                    <span class="score-value">${total}</span>
                                </div>
                            `;
                        }).join('')}
                    </div>

                    <div class="scoreboard-actions">
                        ${!isGameOver ? `
                            <button id="next-round" class="btn btn-primary">Next Round</button>
                            <button id="end-game" class="btn-text" style="margin-top: 32px; color: var(--danger);">End Game</button>
                        ` : `
                            <button onclick="location.hash=''" class="btn btn-primary">Home</button>
                        `}
                    </div>
                </div>
            `;

            if (!isGameOver) {
                container.querySelector('#next-round').addEventListener('click', async () => {
                    try {
                        await nextRound(gameId);
                        const updated = await getGame(gameId);
                        game.current_round = updated.current_round;
                        game.dealer_index = updated.dealer_index;
                        game.phase = updated.phase;
                        currentIndex = 0;
                        scores = {};
                        renderEntry();
                    } catch (error) {
                        alert(error.message);
                    }
                });

                container.querySelector('#end-game').addEventListener('click', async () => {
                    if (confirm('End this game?')) {
                        try {
                            await endGame(gameId);
                            navigate(`final/${gameId}`);
                        } catch (error) {
                            alert(error.message);
                        }
                    }
                });
            }
        }

        if (phase === 'scoreboard') {
            renderScoreboard();
        } else {
            renderEntry();
        }
    },

    unmount() {},
};
