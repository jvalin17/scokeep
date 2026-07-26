// Stats screen — leaderboard, game history, bid accuracy, head-to-head

import { getPlaygroundStats } from '../api.js';

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

        function render() {
            container.innerHTML = `
                <div class="stats">
                    <div class="round-info">
                        <span>Stats</span>
                        <span>${stats.total_games} game${stats.total_games !== 1 ? 's' : ''}</span>
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
                        <div class="stats-game-card">
                            <div class="stats-game-header">
                                <span class="stats-muted">${g.date ? new Date(g.date).toLocaleDateString() : '—'}</span>
                                <span>${g.rounds_played} rounds</span>
                                <span class="stats-mode">${g.mode}</span>
                            </div>
                            <div class="stats-game-scores">
                                ${g.players.map(name => `
                                    <div class="stats-game-player ${name === g.winner ? 'stats-game-winner' : ''}">
                                        <span>${name}</span>
                                        <span>${g.scores[name]}${name === g.winner ? ' 👑' : ''}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        render();
    },

    unmount() {},
};
