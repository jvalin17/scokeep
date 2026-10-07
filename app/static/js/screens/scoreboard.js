// Scoreboard screen — cumulative scores, next round / end game

import { getApi } from '../resolve-api.js';
import { getTrump, escapeHtml } from '../components/game-utils.js';
import { soundNextRound, soundEndGame, soundUndo } from '../components/sounds.js';
import { renderScoresheetTable } from '../components/screen-parts.js';

export const scoreboardScreen = {
    async mount(container, state, { navigate, params }) {
        const gameId = params[0];
        const api = await getApi(gameId);
        const game = await api.getGame(gameId);
        if (!game) { navigate(''); return; }
        // Scoreboard accepts scoreboard, intermission (Scoresheet totals-off), and finished
        const onBoard =
            game.phase === 'scoreboard' ||
            game.phase === 'intermission' ||
            game.status === 'finished';
        if (!onBoard) {
            await api.resyncGame(gameId);
            return;
        }
        state.game = game;

        const scoreboard = await api.getScoreboard(gameId);
        const players = game.players;
        const totals = scoreboard.totals;
        const rounds = scoreboard.rounds;

        const isScoresheet = (game.settings?.game_type || 'kachuful') === 'scoresheet';
        const hideStandings = game.phase === 'intermission' || (isScoresheet && game.settings?.show_totals === false);

        // current_round = round just completed (not yet advanced by next-round)
        const roundsPerSet = game.settings.rounds_per_set || 8;
        const isSetEnd = !isScoresheet && game.current_round % roundsPerSet === 0;
        const isLastRound = !isScoresheet && game.current_round >= game.total_rounds;
        const isGameOver = game.status === 'finished';

        const appearance = game.settings.appearance || 'standard';
        document.body.setAttribute('data-phase', 'scoreboard');
        document.body.setAttribute('data-appearance', appearance);
        document.body.setAttribute(
            'data-game-type',
            game.settings.game_type || 'kachuful',
        );

        // Build score display
        let scoreTableHtml = '';
        let winnerHtml = '';
        if (rounds.length === 0 && isGameOver) {
            scoreTableHtml = `<p style="text-align:center;color:var(--text-muted);padding:24px 0;">No rounds played</p>`;
        } else if (rounds.length > 0 && isGameOver) {
            // Winner celebration
            const lowestWins = game.settings?.winner === 'lowest';
            const standings = players.map((name, index) => ({
                name, score: totals[String(index)] || 0,
            })).sort((a, b) => (lowestWins ? a.score - b.score : b.score - a.score));
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
                            <span class="rank-name">${escapeHtml(player.name)}</span>
                            <span class="rank-score">${player.score}</span>
                        </div>
                    `).join('')}
                </div>
            `;

            winnerHtml = `
                <div class="final-celebration">
                    <div class="confetti-container">${confettiPieces}</div>
                    <div class="final-trophy">🏆</div>
                    <h2 class="final-winner">${escapeHtml(winner.name)}</h2>
                    <p class="final-score">${winner.score} points</p>
                </div>
            `;

            // Game over: full scoresheet — round scores only, total at bottom
            scoreTableHtml = `
                ${renderScoresheetTable(players, rounds, totals)}
                ${rankingsHtml}
            `;
        } else if (rounds.length > 0 && !hideStandings) {
            // Between rounds: round score only — no grand total
            const lastRound = rounds[rounds.length - 1];
            scoreTableHtml = `
                <div class="score-table" id="scoreboard-standings" data-standings="1">
                    <div class="score-header">
                        <span>Player</span>
                        <span>Round ${lastRound.round_num}</span>
                    </div>
                    ${players.map((name, index) => {
                        const key = String(index);
                        const score = lastRound.scores[key] || 0;
                        return `
                            <div class="score-row">
                                <span>${escapeHtml(name)}</span>
                                <span class="score-value ${score < 0 ? 'score-negative' : ''}">${score > 0 ? '+' : ''}${score}</span>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        } else if (hideStandings && !isGameOver) {
            scoreTableHtml = `<p class="claimed-info" data-intermission="1" style="text-align:center;padding:16px;">Round locked — totals hidden</p>`;
        }

        container.innerHTML = `
            <div class="scoreboard">
                ${isGameOver ? winnerHtml : `
                    <div class="round-info">
                        <span>After Round ${game.current_round}</span>
                        ${state.playground ? `<button class="btn-home" data-nav="playground/${state.playground.share_code}" aria-label="Back to room">🏠</button>` : ''}
                    </div>
                `}

                ${scoreTableHtml}

                <div class="scoreboard-actions">
                    ${isGameOver ? `
                        <button class="btn btn-primary" data-nav="${state.playground ? `playground/${state.playground.share_code}` : ''}">🏠 Back to Room</button>
                    ` : `
                        <button id="next-round" class="btn btn-primary">${isScoresheet ? 'Next Round' : (isLastRound ? 'Finish Game' : 'Next Round')}</button>
                        ${!isScoresheet && isLastRound ? '<button id="extend-set" class="btn" style="margin-top: 12px;">Add a Set</button>' : ''}
                        ${isScoresheet ? '' : '<button id="edit-hands" class="btn-text" style="margin-top: 16px;">Edit Hands</button>'}
                        <button id="end-game" class="btn-text" style="margin-top: 16px; color: var(--danger);">${isScoresheet ? 'Finished' : 'End Game'}</button>
                        <button id="undo-round" class="btn-text">${isScoresheet ? 'Undo Last Round' : 'Undo Last Round'}</button>
                        ${isScoresheet ? '<button id="edit-round" class="btn-text" style="margin-top: 8px;">Edit Round</button>' : ''}
                    `}
                </div>
                <p id="scoreboard-error" class="error hidden"></p>
            </div>
        `;

        // Bind data-nav buttons
        container.querySelectorAll('[data-nav]').forEach(el => {
            el.addEventListener('click', () => { location.hash = el.dataset.nav; });
        });

        if (!isGameOver) {
            const nextRoundBtn = container.querySelector('#next-round');
            if (nextRoundBtn) {
                nextRoundBtn.addEventListener('click', async () => {
                    try {
                        const updated = await api.nextRound(gameId);
                        if (updated.phase === 'review') {
                            navigate(`review/${gameId}`);
                        } else if (updated.phase === 'entry') {
                            soundNextRound();
                            navigate(`entry/${gameId}`);
                        } else {
                            soundNextRound();
                            navigate(`bid/${gameId}`);
                        }
                    } catch (error) {
                        showError(error.message);
                    }
                });
            }

            const editHandsBtn = container.querySelector('#edit-hands');
            if (editHandsBtn) {
                editHandsBtn.addEventListener('click', async () => {
                    try {
                        await api.enterRescore(gameId);
                        state.rescore = true;
                        navigate(`roundend/${gameId}`);
                    } catch (error) {
                        showError(error.message);
                    }
                });
            }

            const endGameBtn = container.querySelector('#end-game');
            if (endGameBtn) {
                endGameBtn.addEventListener('click', async () => {
                    try {
                        await api.endGame(gameId);
                        navigate(`review/${gameId}`);
                    } catch (error) {
                        showError(error.message);
                    }
                });
            }

            const extendBtn = container.querySelector('#extend-set');
            if (extendBtn) {
                extendBtn.addEventListener('click', async () => {
                    try {
                        await api.extendGame(gameId);
                        await api.nextRound(gameId);
                        soundNextRound();
                        navigate(`bid/${gameId}`);
                    } catch (error) {
                        showError(error.message);
                    }
                });
            }

            const undoBtn = container.querySelector('#undo-round');
            if (undoBtn) {
                undoBtn.addEventListener('click', async () => {
                    try {
                        await api.undoRound(gameId);
                        soundUndo();
                        const updated = await api.getGame(gameId);
                        if (isScoresheet && updated.phase === 'entry') {
                            navigate(`entry/${gameId}`);
                        } else if (updated.phase === 'bidding') {
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

            const editRoundBtn = container.querySelector('#edit-round');
            if (editRoundBtn) {
                editRoundBtn.addEventListener('click', async () => {
                    try {
                        await api.undoRound(gameId);
                        const updated = await api.getGame(gameId);
                        if (updated.phase !== 'entry') {
                            updated.phase = 'entry';
                        }
                        navigate(`entry/${gameId}`);
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
