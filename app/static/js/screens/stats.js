// Stats screen — insights (personality cards), awards, game history

import { getPlaygroundStats, clearPlaygroundStats, getScoreboard } from '../api.js';
import { escapeHtml } from '../components/game-utils.js';
import { renderPersonalityCards } from '../components/personality-card.js';
import { renderCareerTable, renderLastGameAwards } from '../components/stats-awards.js';
import { renderGameDetail } from '../components/stats-charts.js';

async function patchScore(gameId, roundNum, playerIndex, score, adminKey) {
    const resp = await fetch(`/api/game/${gameId}/round/${roundNum}/score`, {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json',
            'X-Admin-Key': adminKey,
        },
        credentials: 'same-origin',
        body: JSON.stringify({ player_index: playerIndex, score }),
    });
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: 'Failed' }));
        throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    return resp.json();
}

export const statsScreen = {
    async mount(container, state, { navigate, params }) {
        const shareCode = params[0];
        let stats;
        let editMode = false;
        const adminStorageKey = `scokeep_admin_key_${shareCode}`;
        const storedKey = sessionStorage.getItem(adminStorageKey);
        if (storedKey) {
            try {
                const vr = await fetch('/api/game/admin/verify', {
                    method: 'POST', headers: { 'X-Admin-Key': storedKey }, credentials: 'same-origin',
                });
                editMode = vr.ok;
            } catch { /* not valid */ }
            if (!editMode) sessionStorage.removeItem(adminStorageKey);
        }
        try {
            stats = await getPlaygroundStats(shareCode);
        } catch {
            container.innerHTML = `
                <div class="stats">
                    <div class="round-info"><span>Stats</span></div>
                    <p class="stats-empty">No games played yet. Play some rounds first!</p>
                    <button class="btn btn-primary btn-back">Back</button>
                </div>
            `;
            container.querySelector('.btn-back').addEventListener('click', () => history.back());
            return;
        }

        if (stats.total_games === 0) {
            container.innerHTML = `
                <div class="stats">
                    <div class="round-info"><span>Stats</span></div>
                    <p class="stats-empty">No games played yet. Play some rounds first!</p>
                    <button class="btn btn-primary btn-back">Back</button>
                </div>
            `;
            container.querySelector('.btn-back').addEventListener('click', () => history.back());
            return;
        }

        let activeTab = 'insights';
        let expandedGameId = null;
        let expandedData = null;

        function render() {
            const modeClass = editMode ? 'edit-mode' : '';
            container.innerHTML = `
                <div class="stats ${modeClass}">
                    <div class="round-info">
                        <span>Stats</span>
                        <span>${stats.total_games} game${stats.total_games !== 1 ? 's' : ''}</span>
                        <button class="btn-refresh" id="stats-gear" title="Settings">⚙</button>
                    </div>
                    ${editMode ? '<div class="edit-mode-bar">✏️ Edit Mode — tap scores to correct</div>' : ''}

                    <div class="action-overlay hidden">
                        <div class="action-dialog">
                            <button class="action-dialog-close">&times;</button>
                            <button class="action-btn action-btn-warning" id="toggle-edit">${editMode ? '✏️ Exit Edit Mode' : '✏️ Edit Mode'}</button>
                            <div id="edit-auth-slot"></div>
                            <button class="action-btn action-btn-danger" id="clear-stats">🗑️ Clear All Stats</button>
                            <div class="clear-warning hidden">
                                <p class="clear-warning-text">⚠️ Data cannot be recovered. Type <strong>DELETE</strong> to confirm.</p>
                                <input type="text" id="clear-confirm-input" placeholder="Type DELETE" autocomplete="off" class="clear-confirm-input">
                                <div class="clear-actions">
                                    <button class="action-btn action-btn-cancel" id="clear-cancel">Cancel</button>
                                    <button class="action-btn action-btn-danger-confirm" id="clear-proceed" disabled>Proceed</button>
                                </div>
                            </div>
                        </div>
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

                    <button class="btn btn-primary btn-back" style="margin-top: 16px;">Back</button>
                </div>
            `;

            bindListeners();
        }

        function bindListeners() {
            // Tab switching
            container.querySelectorAll('.stats-tab').forEach(tab => {
                tab.addEventListener('click', () => { activeTab = tab.dataset.tab; render(); });
            });

            // Back buttons
            container.querySelectorAll('.btn-back').forEach(b => {
                b.addEventListener('click', () => history.back());
            });

            // Card flip (insights tab)
            if (activeTab === 'insights') {
                container.querySelectorAll('.personality-card:not(.personality-card-locked)').forEach(card => {
                    let flipping = false;
                    card.addEventListener('click', () => {
                        if (flipping) return;
                        flipping = true;
                        card.classList.toggle('flipped');
                        setTimeout(() => { flipping = false; }, 600);
                    });
                });
            }

            bindSettingsListeners();
            bindHistoryListeners();
            if (editMode) bindEditListeners();
        }

        function bindSettingsListeners() {
            const overlay = container.querySelector('.action-overlay');
            const closeDialog = () => overlay.classList.add('hidden');

            container.querySelector('#stats-gear')?.addEventListener('click', () => overlay.classList.remove('hidden'));
            container.querySelector('.action-dialog-close')?.addEventListener('click', closeDialog);
            overlay.addEventListener('click', (event) => { if (event.target === overlay) closeDialog(); });

            container.querySelector('#toggle-edit')?.addEventListener('click', () => {
                if (editMode) {
                    sessionStorage.removeItem(adminStorageKey);
                    editMode = false;
                    closeDialog();
                    render();
                } else {
                    const slot = container.querySelector('#edit-auth-slot');
                    if (slot.children.length) return;
                    const wrap = document.createElement('div');
                    wrap.className = 'edit-auth';
                    const input = document.createElement('input');
                    input.type = 'password';
                    input.placeholder = 'Admin password';
                    const go = document.createElement('button');
                    go.textContent = 'Go';
                    go.className = 'action-btn action-btn-warning';
                    const submit = async () => {
                        if (!input.value) return;
                        try {
                            const resp = await fetch('/api/game/admin/verify', {
                                method: 'POST',
                                headers: { 'X-Admin-Key': input.value },
                                credentials: 'same-origin',
                            });
                            if (!resp.ok) {
                                input.value = '';
                                input.placeholder = 'Wrong password';
                                input.classList.add('auth-error');
                                return;
                            }
                            sessionStorage.setItem(adminStorageKey, input.value);
                            editMode = true;
                            closeDialog();
                            render();
                        } catch {
                            input.placeholder = 'Error — try again';
                        }
                    };
                    go.addEventListener('click', submit);
                    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') submit(); });
                    wrap.appendChild(input);
                    wrap.appendChild(go);
                    slot.appendChild(wrap);
                    input.focus();
                }
            });

            const clearWarning = container.querySelector('.clear-warning');
            container.querySelector('#clear-stats')?.addEventListener('click', () => clearWarning.classList.remove('hidden'));
            container.querySelector('#clear-cancel')?.addEventListener('click', () => clearWarning.classList.add('hidden'));

            const confirmInput = container.querySelector('#clear-confirm-input');
            const proceedBtn = container.querySelector('#clear-proceed');
            if (confirmInput && proceedBtn) {
                confirmInput.addEventListener('input', () => { proceedBtn.disabled = confirmInput.value !== 'DELETE'; });
                proceedBtn.addEventListener('click', async () => {
                    if (confirmInput.value !== 'DELETE') return;
                    try {
                        await clearPlaygroundStats(shareCode);
                        closeDialog();
                        navigate(`stats/${shareCode}`);
                    } catch {
                        closeDialog();
                        render();
                    }
                });
            }
        }

        function bindHistoryListeners() {
            container.querySelectorAll('.expand-game-btn').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const gameId = Number(btn.dataset.gameId);
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

        function bindEditListeners() {
            container.querySelectorAll('.score-cell').forEach(cell => {
                cell.style.cursor = 'pointer';
                cell.addEventListener('click', async () => {
                    const gameId = Number(cell.dataset.gameId);
                    const roundNum = Number(cell.dataset.round);
                    const playerIdx = Number(cell.dataset.player);
                    const current = Number(cell.dataset.score);
                    const newVal = prompt(`Edit score (round ${roundNum}):`, current);
                    if (newVal === null) return;
                    const parsed = parseInt(newVal, 10);
                    if (isNaN(parsed)) return;
                    const adminKey = sessionStorage.getItem(adminStorageKey);
                    try {
                        await patchScore(gameId, roundNum, playerIdx, parsed, adminKey);
                        expandedData = await getScoreboard(gameId);
                        stats = await getPlaygroundStats(shareCode);
                        render();
                    } catch (err) {
                        if (err.message.includes('Admin')) {
                            sessionStorage.removeItem(adminStorageKey);
                            editMode = false;
                            render();
                        }
                        alert(err.message);
                    }
                });
            });
        }

        // ── Tab content renderers ──

        function renderInsights() {
            const insights = stats.insights;
            if (!insights || !insights.players) {
                return '<p class="stats-empty">Play 3 games to unlock player insights!</p>';
            }
            return renderPersonalityCards(insights.players);
        }

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
                    ${renderCareerTable('Hot Hand', '🔥', 'Longest streak of positive rounds', career.hot_hand, 'longest')}
                    ${renderCareerTable('Biggest Bid', '🎯', 'Highest bid successfully made', career.biggest_bid, 'highest')}
                    ${renderCareerTable('Set Champion', '👑', 'Most points scored in a single set', career.set_champion, 'highest')}
                    ${renderCareerTable('Set Disaster', '💀', 'Most negative points in a single set', career.set_disaster, 'worst')}
                    ${renderCareerTable('Comeback King', '🦅', 'Largest score deficit recovered in a game', career.comeback_king, 'highest')}
                    ${renderCareerTable('Sweep', '🧹', 'Games won (highest score)', career.sweep)}
                    ${renderCareerTable('Iron Wall', '🛡️', 'Longest streak of successful zero bids', career.iron_wall, 'longest')}
                    ${renderCareerTable('Heartbreaker', '💔', 'Rounds where bid was off by exactly 1', career.heartbreaker)}
                    ${renderCareerTable('Endurance', '🏃', 'Total rounds played', career.endurance)}
                    ${renderCareerTable('Triple Crown', '👑', 'Games with best accuracy AND highest score', career.triple_crown)}
                    ${!career.sniper?.some(p => p.count > 0)
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
                                        <span>${escapeHtml(name)}</span>
                                        <span>${g.scores[name]}${name === g.winner ? ' 👑' : ''}</span>
                                    </div>
                                `).join('')}
                            </div>
                            <button class="btn-small expand-game-btn" style="width:100%;margin-top:8px;" data-game-id="${g.game_id}">${expandedGameId === g.game_id ? '▲ Hide scoresheet' : '▼ View scoresheet'}</button>
                            ${expandedGameId === g.game_id ? (
                                expandedData === 'loading' ? '<p class="stats-muted" style="padding:8px;text-align:center;">Loading...</p>' :
                                expandedData === 'error' ? '<p class="stats-muted" style="padding:8px;text-align:center;">Could not load game details</p>' :
                                expandedData ? renderGameDetail(g, expandedData, editMode) : ''
                            ) : ''}
                        </div>
                    `).join('')}
                </div>
            `;
        }

        render();
    },

    unmount() {},
};
