// Stats screen — insights (personality cards), awards, game history

import { getPlaygroundStats, clearPlaygroundStats, getScoreboard } from '../api.js';
import { getTrump } from '../components/game-utils.js';
import { renderPersonalityCards } from '../components/personality-card.js';

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

        let activeTab = 'insights';
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
                        <button class="stats-tab ${activeTab === 'insights' ? 'active' : ''}" data-tab="insights">Insights</button>
                        <button class="stats-tab ${activeTab === 'highlights' ? 'active' : ''}" data-tab="highlights">Awards</button>
                        <button class="stats-tab ${activeTab === 'history' ? 'active' : ''}" data-tab="history">Games</button>
                    </div>

                    <div class="stats-content">
                        ${activeTab === 'insights' ? renderInsights() : ''}
                        ${activeTab === 'highlights' ? renderHighlights() : ''}
                        ${activeTab === 'history' ? renderHistory() : ''}
                    </div>

                    <button class="btn btn-primary" style="margin-top: 16px;" onclick="history.back()">Back</button>
                </div>
            `;

            bindTabListeners();
            bindActionListeners();
            if (activeTab === 'insights') {
                bindCardFlipListeners();
            }
        }

        function bindTabListeners() {
            container.querySelectorAll('.stats-tab').forEach(tab => {
                tab.addEventListener('click', () => {
                    activeTab = tab.dataset.tab;
                    render();
                });
            });
        }

        function bindActionListeners() {
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

        function bindCardFlipListeners() {
            container.querySelectorAll('.personality-card').forEach(card => {
                card.addEventListener('click', () => {
                    card.classList.toggle('flipped');
                });
            });
        }

        // ── Insights tab ──

        function renderInsights() {
            const insights = stats.insights;
            if (!insights || !insights.players) {
                return '<p class="stats-empty">Play 3 games to unlock player insights!</p>';
            }
            return renderPersonalityCards(insights.players);
        }

        // ── Awards tab ──

        function renderHighlights() {
            const highlights = stats.highlights;
            if (!highlights) return '<p class="stats-empty">No highlights yet.</p>';

            const { career } = highlights;

            return `
                <div class="stats-section">
                    ${renderLastGameAwards(highlights.last_game)}

                    <h3 style="margin:20px 0 12px;">Career Records</h3>
                    ${renderCareerTable('Sniper', '🎯', 'Bid exactly 1 and made it', career.sniper)}
                    ${renderCareerTable('Zero Master', '🥷', 'Bid 0 and won no tricks', career.zero_master)}
                    ${renderCareerTable('High Roller', '🎲', 'Bid 3 or more and made it', career.high_roller)}
                    ${renderCareerTable('All-in', '💎', 'Bid all cards dealt and made it', career.all_in)}
                    ${renderCareerTable('Jinxed', '😵', 'Longest streak of missed bids', career.jinxed, 'longest')}
                    ${renderCareerTable('Perfect Set', '⭐', 'Made every bid in a full set', career.perfect_set)}

                    ${!career.sniper?.some(p => p.count > 0)
                        ? '<p class="stats-muted">Play more games to unlock awards!</p>'
                        : ''}
                </div>
            `;
        }

        function renderCareerTable(title, emoji, description, data, valueKey = 'count') {
            if (!data || !data.length) return '';
            const filtered = data.filter(p => p[valueKey] > 0);
            if (!filtered.length) return '';
            return `
                <div class="stats-card" style="margin-bottom:16px;padding:12px;">
                    <h4 style="margin:0 0 4px;">${emoji} ${title}</h4>
                    <p class="stats-muted" style="font-size:0.75rem;margin-bottom:8px;">${description}</p>
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

        function renderLastGameAwards(lastGame) {
            if (!lastGame) return '';
            const awards = [
                { key: 'mvp', emoji: '🏆', title: 'MVP', desc: 'Highest total score', detail: lg => `${lg.score} points` },
                { key: 'sharpshooter', emoji: '🎯', title: 'Sharpshooter', desc: 'Best bid accuracy', detail: lg => `${lg.accuracy}% accuracy` },
                { key: 'brick_wall', emoji: '🧱', title: 'Brick Wall', desc: 'Most successful zero bids', detail: lg => `${lg.count} zero-bids made` },
                { key: 'bold_move', emoji: '🎲', title: 'Bold Move', desc: 'Highest bid that was made', detail: lg => `bid ${lg.bid} and made it` },
                { key: 'sandbagger', emoji: '🏖️', title: 'Sandbagger', desc: 'Most underbids — bid low, won more', detail: lg => `${lg.count} underbids` },
                { key: 'gambler', emoji: '🎰', title: 'Gambler', desc: 'Most overbids — bid high, fell short', detail: lg => `${lg.count} overbids` },
                { key: 'cursed', emoji: '😵', title: 'Cursed', desc: 'Longest streak of missed bids', detail: lg => `${lg.streak} misses in a row` },
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
                            <div class="stats-muted" style="margin-top:2px;font-size:0.7rem;">${a.desc}</div>
                            <div class="stats-muted" style="margin-top:2px;font-size:0.8rem;">
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

        // ── Games tab ──

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
                                    const trump = getTrump(round.round_num);
                                    return `<tr>
                                        <td>${round.round_num}<span class="${trump.isRed ? 'trump-red' : ''}" style="font-size:0.7em;">${trump.symbol}</span></td>
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
