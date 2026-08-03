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
                        <button class="stats-tab ${activeTab === 'trends' ? 'active' : ''}" data-tab="trends">Trends</button>
                        <button class="stats-tab ${activeTab === 'highlights' ? 'active' : ''}" data-tab="highlights">Awards</button>
                        <button class="stats-tab ${activeTab === 'history' ? 'active' : ''}" data-tab="history">Games</button>
                    </div>

                    <div class="stats-content">
                        ${activeTab === 'leaderboard' ? renderLeaderboard() : ''}
                        ${activeTab === 'accuracy' ? renderAccuracy() : ''}
                        ${activeTab === 'trends' ? renderTrends() : ''}
                        ${activeTab === 'highlights' ? renderHighlights() : ''}
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
            window._expandGame = async (gameId) => {
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
            };
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

        function renderTrends() {
            const trends = stats.trends;
            if (!trends || !trends.length) return '<p class="stats-empty">No trend data yet.</p>';
            return `
                <div class="stats-section">
                    <h3 style="margin-bottom: 12px;">Win Streaks</h3>
                    ${trends.map(t => `
                        <div class="stats-bar-row">
                            <span class="stats-bar-name">${t.name}</span>
                            <span class="stats-bar-value">${t.current_streak > 0 ? '🔥 ' + t.current_streak : '—'}</span>
                            <span class="stats-muted" style="min-width:60px;text-align:right;">best: ${t.longest_streak}</span>
                        </div>
                    `).join('')}

                    <h3 style="margin: 20px 0 12px;">Overbid / Underbid</h3>
                    ${trends.filter(t => t.total_bid_rounds > 0).map(t => {
                        const total = t.overbids + t.underbids;
                        const exact = t.total_bid_rounds - total;
                        const obPct = total > 0 ? Math.round(t.overbids / t.total_bid_rounds * 100) : 0;
                        const ubPct = total > 0 ? Math.round(t.underbids / t.total_bid_rounds * 100) : 0;
                        const exPct = 100 - obPct - ubPct;
                        const style = t.overbids > t.underbids ? 'Aggressive' : t.underbids > t.overbids ? 'Conservative' : 'Balanced';
                        return `
                            <div class="stats-card" style="margin-bottom:8px;">
                                <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                                    <span>${t.name}</span>
                                    <span class="stats-muted">${style}</span>
                                </div>
                                <div class="stats-bar-track" style="display:flex;height:8px;border-radius:4px;overflow:hidden;">
                                    <div style="width:${obPct}%;background:#BBDEFB;" title="Overbid ${obPct}%"></div>
                                    <div style="width:${exPct}%;background:#C8E6C9;" title="Exact ${exPct}%"></div>
                                    <div style="width:${ubPct}%;background:#FFE0B2;" title="Underbid ${ubPct}%"></div>
                                </div>
                                <div style="font-size:0.75rem;color:var(--text-muted);margin-top:6px;line-height:1.6;">
                                    <div>Overbid: ${t.overbids} rounds</div>
                                    <div>Exact: ${exact} rounds</div>
                                    <div>Underbid: ${t.underbids} rounds</div>
                                </div>
                            </div>
                        `;
                    }).join('')}

                    <h3 style="margin: 20px 0 12px;">Clutch Factor</h3>
                    ${trends.filter(t => t.clutch_opportunities > 0).length === 0
                        ? '<p class="stats-muted">Need more games for clutch data</p>'
                        : trends.filter(t => t.clutch_opportunities > 0).map(t => {
                            const pct = Math.round(t.clutch_wins / t.clutch_opportunities * 100);
                            return `
                                <div class="stats-bar-row">
                                    <span class="stats-bar-name">${t.name}</span>
                                    <div class="stats-bar-track">
                                        <div class="stats-bar-fill ${pct >= 50 ? 'stats-bar-good' : ''}" style="width: ${pct}%"></div>
                                    </div>
                                    <span class="stats-bar-value">${pct}% (${t.clutch_wins}/${t.clutch_opportunities})</span>
                                </div>
                            `;
                        }).join('')
                    }
                </div>
            `;
        }

        function renderHighlights() {
            const highlights = stats.highlights;
            if (!highlights) return '<p class="stats-empty">No highlights yet.</p>';

            const { career, recent } = highlights;

            function careerTable(title, emoji, data, valueKey = 'count') {
                if (!data || !data.length) return '';
                const filtered = data.filter(p => p[valueKey] > 0);
                if (!filtered.length) return '';
                return `
                    <div class="stats-card" style="margin-bottom:16px;padding:12px;">
                        <h4 style="margin:0 0 10px;">${emoji} ${title}</h4>
                        <table class="awards-table">
                            <thead>
                                <tr><th>#</th><th>Player</th><th>Count</th></tr>
                            </thead>
                            <tbody>
                                ${filtered.map((p, i) => `
                                    <tr>
                                        <td>${i + 1}</td>
                                        <td>${p.name}</td>
                                        <td><strong>${p[valueKey]}</strong></td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                `;
            }

            function recentCard(title, emoji, data) {
                if (!data) return '';
                let detail = '';
                if (data.score !== undefined) {
                    detail = `+${data.score} in Round ${data.round}`;
                } else if (data.accuracy !== undefined) {
                    detail = `${data.accuracy}% accuracy`;
                } else if (data.count !== undefined) {
                    detail = `${data.count} in a row`;
                }
                return `
                    <div class="stats-card" style="margin-bottom:8px;padding:10px 12px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <span>${emoji} ${title}</span>
                            <strong style="margin-left:8px;">${data.name}</strong>
                        </div>
                        <div class="stats-muted" style="margin-top:4px;font-size:0.8rem;">
                            ${detail}
                        </div>
                    </div>
                `;
            }

            function lastGameSection(lastGame) {
                if (!lastGame) return '';
                const awards = [
                    { key: 'mvp', emoji: '🏆', title: 'MVP', detail: lg => `${lg.score} points` },
                    { key: 'sharpshooter', emoji: '🎯', title: 'Sharpshooter', detail: lg => `${lg.accuracy}% accuracy` },
                    { key: 'brick_wall', emoji: '🧱', title: 'Brick Wall', detail: lg => `${lg.count} zero-bids made` },
                    { key: 'bold_move', emoji: '🎲', title: 'Bold Move', detail: lg => `bid ${lg.bid} and made it` },
                    { key: 'sandbagger', emoji: '🏖️', title: 'Sandbagger', detail: lg => `${lg.count} underbids` },
                    { key: 'gambler', emoji: '🎰', title: 'Gambler', detail: lg => `${lg.count} overbids` },
                    { key: 'cursed', emoji: '😵', title: 'Cursed', detail: lg => `${lg.streak} misses in a row` },
                ];
                const cards = awards
                    .filter(a => lastGame[a.key])
                    .map(a => {
                        const data = lastGame[a.key];
                        return `
                            <div class="stats-card" style="margin-bottom:8px;padding:10px 12px;">
                                <div style="display:flex;justify-content:space-between;align-items:center;">
                                    <span>${a.emoji} ${a.title}</span>
                                    <strong style="margin-left:8px;">${data.name}</strong>
                                </div>
                                <div class="stats-muted" style="margin-top:4px;font-size:0.8rem;">
                                    ${a.detail(data)}
                                </div>
                            </div>
                        `;
                    }).join('');
                return `
                    <h3 style="margin-bottom:12px;">Last Game</h3>
                    ${cards}
                `;
            }

            const hasRecent = recent.hot_hand || recent.on_fire
                || recent.streak || recent.dodger;

            return `
                <div class="stats-section">
                    ${lastGameSection(highlights.last_game)}

                    ${hasRecent ? `
                        <h3 style="margin:20px 0 12px;">Recent Form (last 3 games)</h3>
                        ${recentCard('Hot Hand', '🔥', recent.hot_hand)}
                        ${recentCard('On Fire', '🎯', recent.on_fire)}
                        ${recentCard('Streak', '⚡', recent.streak)}
                        ${recentCard('Dodger', '🥷', recent.dodger)}
                    ` : ''}

                    <h3 style="margin:20px 0 12px;">Career Records</h3>
                    ${careerTable('Sniper', '🎯', career.sniper)}
                    ${careerTable('Zero Master', '🥷', career.zero_master)}
                    ${careerTable('High Roller', '🎲', career.high_roller)}
                    ${careerTable('All-in', '💎', career.all_in)}
                    ${careerTable('Jinxed', '😵', career.jinxed, 'longest')}
                    ${careerTable('Perfect Set', '⭐', career.perfect_set)}

                    ${!hasRecent && !career.sniper?.some(p => p.count > 0)
                        ? '<p class="stats-muted">Play more games to unlock awards!</p>'
                        : ''}
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
                            <button class="btn-small" style="width:100%;margin-top:8px;" onclick="window._expandGame(${g.game_id})">${expandedGameId === g.game_id ? '▲ Hide scoresheet' : '▼ View scoresheet'}</button>
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
