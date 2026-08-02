// Stats screen — leaderboard, game history, bid accuracy, head-to-head

import { getPlaygroundStats, clearPlaygroundStats, getScoreboard } from '../api.js';

export const statsScreen = {
    async mount(container, state, { navigate, params }) {
        const shareCode = params[0];
        let stats;
        try {
            stats = await getPlaygroundStats(shareCode);
        } catch {
            container.innerHTML = `
                <div class="stats">
                    <div class="round-info"><span>Stats</span></div>
                    <p class="stats-empty">No games played yet. Play some rounds first!</p>
                    <button class="btn btn-primary" onclick="history.back()">Back</button>
                </div>
            `;
            return;
        }

        if (stats.total_games === 0) {
            container.innerHTML = `
                <div class="stats">
                    <div class="round-info"><span>Stats</span></div>
                    <p class="stats-empty">No games played yet. Play some rounds first!</p>
                    <button class="btn btn-primary" onclick="history.back()">Back</button>
                </div>
            `;
            return;
        }

        let activeTab = 'leaderboard';
        let expandedGameId = null;
        let expandedData = null;

        function render() {
            container.innerHTML = `
                <div class="stats">
                    <div class="round-info">
                        <span>Stats</span>
                        <span>${stats.total_games} game${stats.total_games !== 1 ? 's' : ''}</span>
                        <button class="btn-refresh" id="stats-gear" title="Settings">⚙</button>
                    </div>
                    <div id="stats-actions" class="stats-actions hidden">
                        <button class="btn btn-danger" id="clear-stats">Clear All Stats</button>
                    </div>

                    <div class="stats-tabs">
                        <button class="stats-tab ${activeTab === 'leaderboard' ? 'active' : ''}" data-tab="leaderboard">Leaderboard</button>
                        <button class="stats-tab ${activeTab === 'accuracy' ? 'active' : ''}" data-tab="accuracy">Accuracy</button>
                        <button class="stats-tab ${activeTab === 'h2h' ? 'active' : ''}" data-tab="h2h">Head-to-Head</button>
                        <button class="stats-tab ${activeTab === 'history' ? 'active' : ''}" data-tab="history">Games</button>
                    </div>

                    <div class="stats-content">
                        ${activeTab === 'leaderboard' ? renderLeaderboard() : ''}
                        ${activeTab === 'accuracy' ? renderAccuracy() : ''}
                        ${activeTab === 'h2h' ? renderH2H() : ''}
                        ${activeTab === 'history' ? renderHistory() : ''}
                    </div>

                    <button class="btn btn-primary" style="margin-top: 16px;" onclick="history.back()">Back</button>
                </div>
            `;

            container.querySelectorAll('.stats-tab').forEach(tab => {
                tab.addEventListener('click', () => {
                    activeTab = tab.dataset.tab;
                    render();
                });
            });

            const gearBtn = container.querySelector('#stats-gear');
            if (gearBtn) {
                gearBtn.addEventListener('click', () => {
                    const actions = container.querySelector('#stats-actions');
                    actions.classList.toggle('hidden');
                });
            }

            const clearBtn = container.querySelector('#clear-stats');
            if (clearBtn) {
                clearBtn.addEventListener('click', async () => {
                    if (!confirm('Clear all game history and stats for this room? This cannot be undone.')) return;
                    try {
                        await clearPlaygroundStats(shareCode);
                        navigate(`stats/${shareCode}`);
                    } catch {
                        /* clear failed silently — user can retry */
                    }
                });
            }

            // Expand game detail in history tab
            container.querySelectorAll('[data-game]').forEach(card => {
                card.addEventListener('click', async (event) => {
                    event.stopPropagation();
                    const gameId = parseInt(card.dataset.game);
                    if (expandedGameId === gameId) {
                        expandedGameId = null;
                        expandedData = null;
                    } else {
                        expandedGameId = gameId;
                        expandedData = 'loading';
                        render();
                        try {
                            expandedData = await getScoreboard(gameId);
                        } catch {
                            expandedData = 'error';
                        }
                    }
                    render();
                });
            });
        }

        function renderLeaderboard() {
            const lb = stats.leaderboard;
            return `
                <div class="stats-section">
                    ${lb.map((p, i) => `
                        <div class="stats-card ${i === 0 ? 'stats-first' : ''}">
                            <div class="stats-rank">${i === 0 ? '👑' : i + 1}</div>
                            <div class="stats-card-body">
                                <div class="stats-name">${p.name}</div>
                                <div class="stats-detail">
                                    <span>${p.wins}W / ${p.games_played}G</span>
                                    <span class="stats-highlight">${p.win_rate}% win</span>
                                </div>
                                <div class="stats-detail">
                                    <span>Total: ${p.total_score}</span>
                                    <span>Avg: ${p.avg_score_per_round}/rnd</span>
                                </div>
                                <div class="stats-detail stats-muted">
                                    Best: ${p.best_game} &nbsp; Worst: ${p.worst_game}
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        function renderAccuracy() {
            const lb = stats.leaderboard.slice().sort((a, b) => b.bid_accuracy - a.bid_accuracy);
            return `
                <div class="stats-section">
                    <h3 style="margin-bottom: 12px;">Bid Accuracy</h3>
                    ${lb.map(p => {
                        const pct = p.bid_accuracy;
                        return `
                            <div class="stats-bar-row">
                                <span class="stats-bar-name">${p.name}</span>
                                <div class="stats-bar-track">
                                    <div class="stats-bar-fill ${pct >= 50 ? 'stats-bar-good' : ''}" style="width: ${pct}%"></div>
                                </div>
                                <span class="stats-bar-value">${pct}%</span>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        }

        function renderH2H() {
            const h2h = stats.head_to_head;
            if (!h2h.length) return '<p class="stats-empty">No head-to-head data yet.</p>';
            return `
                <div class="stats-section">
                    ${h2h.map(match => {
                        const [p1, p2] = match.players;
                        const r = match.record;
                        return `
                            <div class="stats-h2h-card">
                                <div class="h2h-player ${r[p1] > r[p2] ? 'h2h-leader' : ''}">${p1}<br><strong>${r[p1]}</strong></div>
                                <div class="h2h-vs">vs<br><span class="stats-muted">${r.games}g</span></div>
                                <div class="h2h-player ${r[p2] > r[p1] ? 'h2h-leader' : ''}">${p2}<br><strong>${r[p2]}</strong></div>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        }

        function renderHistory() {
            return `
                <div class="stats-section">
                    ${stats.game_history.map(g => `
                        <div class="stats-game-card" data-game="${g.game_id}" style="cursor:pointer;">
                            <div class="stats-game-header">
                                <span class="stats-muted">${g.date ? new Date(g.date).toLocaleDateString() : '—'}</span>
                                <span>${g.rounds_played} rounds</span>
                                <span class="stats-mode">${g.mode}</span>
                                <span>${expandedGameId === g.game_id ? '▲' : '▼'}</span>
                            </div>
                            <div class="stats-game-scores">
                                ${g.players.map(name => `
                                    <div class="stats-game-player ${name === g.winner ? 'stats-game-winner' : ''}">
                                        <span>${name}</span>
                                        <span>${g.scores[name]}${name === g.winner ? ' 👑' : ''}</span>
                                    </div>
                                `).join('')}
                            </div>
                            ${expandedGameId === g.game_id ? (
                                expandedData === 'loading' ? '<p class="stats-muted" style="padding:8px;text-align:center;">Loading...</p>' :
                                expandedData === 'error' ? '<p class="stats-muted" style="padding:8px;text-align:center;">Could not load game details</p>' :
                                expandedData ? renderGameDetail(g, expandedData) : ''
                            ) : ''}
                        </div>
                    `).join('')}
                </div>
            `;
        }

        function renderGameDetail(game, scoreboard) {
            const players = game.players;
            const rounds = scoreboard.rounds;
            const totals = scoreboard.totals;
            if (!rounds.length) return '<p class="stats-muted" style="padding:8px;">No round data</p>';

            return `
                <div class="game-detail">
                    <div class="game-detail-legend">
                        <span class="legend-item"><span class="legend-swatch legend-overbid"></span> Overbid</span>
                        <span class="legend-item"><span class="legend-swatch legend-underbid"></span> Underbid</span>
                    </div>
                    <div class="score-table-full" style="margin-top:8px;">
                        <table class="scoresheet">
                            <thead>
                                <tr>
                                    <th>R#</th>
                                    ${players.map(name => `<th>${name}</th>`).join('')}
                                </tr>
                            </thead>
                            <tbody>
                                ${rounds.map(round => {
                                    return `<tr>
                                        <td>${round.round_num}</td>
                                        ${players.map((_, idx) => {
                                            const key = String(idx);
                                            const score = round.scores[key] || 0;
                                            const bid = round.bids ? round.bids[key] : null;
                                            const hand = round.hands_won ? round.hands_won[key] : null;
                                            let cellClass = '';
                                            if (bid !== null && hand !== null && bid !== hand) {
                                                cellClass = bid > hand ? 'cell-overbid' : 'cell-underbid';
                                            }
                                            return `<td class="${cellClass} ${score < 0 ? 'score-negative' : ''}">
                                                ${score > 0 ? '+' : ''}${score}
                                            </td>`;
                                        }).join('')}
                                    </tr>`;
                                }).join('')}
                            </tbody>
                            <tfoot>
                                <tr class="totals-row">
                                    <td><strong>Tot</strong></td>
                                    ${players.map((_, idx) => `<td><strong>${totals[String(idx)] || 0}</strong></td>`).join('')}
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                </div>
            `;
        }

        render();
    },

    unmount() {},
};
