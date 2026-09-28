// Career awards + last game awards rendering for stats screen

import { escapeHtml } from './game-utils.js';

const PODIUM_INFO =
    'Weighted finishes — place points plus margin for how far you beat the field. '
    + 'Last place still scores. Standing = average per game.';

function renderInfoBtn(description) {
    if (!description) return '';
    return `
        <button type="button" class="stats-info-btn" aria-label="About"
            aria-expanded="false" data-info="${escapeHtml(description)}">ℹ</button>
    `;
}

export function renderCareerTable(title, emoji, description, data, valueKey = 'count') {
    if (!data || !data.length) return '';
    const headerLabels = {
        count: 'Count', longest: 'Streak', highest: 'Best', worst: 'Worst',
    };
    const header = headerLabels[valueKey] || 'Value';
    const filtered = valueKey === 'worst'
        ? data.filter(p => p[valueKey] < 0)
        : data.filter(p => p[valueKey] > 0);
    if (!filtered.length) return '';
    const displayVal = (v) => valueKey === 'worst' ? v : v;
    return `
        <div class="stats-card awards-card">
            <div class="awards-card-header">
                <h4 class="awards-card-title">${emoji} ${title}</h4>
                ${renderInfoBtn(description)}
            </div>
            <p class="stats-info-tip" hidden></p>
            <table class="awards-table">
                <thead>
                    <tr><th>#</th><th>Player</th><th>${header}</th></tr>
                </thead>
                <tbody>
                    ${filtered.map((p, i) => `
                        <tr>
                            <td>${i + 1}</td>
                            <td>${escapeHtml(p.name)}</td>
                            <td><strong>${displayVal(p[valueKey])}</strong></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

export function renderLastGameAwards(lastGame) {
    if (!lastGame) return '';
    // New titles array format
    if (lastGame.titles && Array.isArray(lastGame.titles)) {
        const cards = lastGame.titles.map(t => `
            <div class="stats-card awards-card awards-card-compact">
                <div class="awards-card-header">
                    <span class="awards-card-title">${escapeHtml(t.emoji)} ${escapeHtml(t.title)}</span>
                    <strong class="awards-card-player">${escapeHtml(t.player)}</strong>
                    ${renderInfoBtn(t.desc)}
                </div>
                <p class="stats-info-tip" hidden></p>
                <div class="stats-muted awards-card-detail">${escapeHtml(t.detail)}</div>
            </div>
        `).join('');
        return `
            <h3 style="margin-bottom:12px;">Last Game</h3>
            ${cards}
        `;
    }
    // Legacy format fallback (cached data)
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
                <div class="stats-card awards-card awards-card-compact">
                    <div class="awards-card-header">
                        <span class="awards-card-title">${a.emoji} ${a.title}</span>
                        <strong class="awards-card-player">${escapeHtml(data.name)}</strong>
                        ${renderInfoBtn(a.desc)}
                    </div>
                    <p class="stats-info-tip" hidden></p>
                    <div class="stats-muted awards-card-detail">${escapeHtml(a.detail(data))}</div>
                </div>
            `;
        }).join('');
    return `
        <h3 style="margin-bottom:12px;">Last Game</h3>
        ${cards}
    `;
}

/** The Podium — weighted finish standing (base place + margin). */
export function renderPodiumBoard(podium) {
    if (!podium || !podium.length) return '';
    const maxPlace = Math.max(
        1,
        ...podium.flatMap((row) => Object.keys(row.places || {}).map(Number)),
    );
    // Always show P1..Pmax so 5–8 player rooms keep a full place grid
    const placeKeys = Array.from({ length: maxPlace }, (_, i) => i + 1);
    const placeHeaders = placeKeys.map((p) => `<th>P${p}</th>`).join('');
    const rows = podium.map((row, i) => {
        const placeCells = placeKeys.map((p) => {
            const places = row.places || {};
            const n = places[p] ?? places[String(p)] ?? 0;
            return `<td>${n || '–'}</td>`;
        }).join('');
        return `
            <tr>
                <td class="podium-sticky-rank">${i + 1}</td>
                <td class="podium-sticky-name">${escapeHtml(row.player)}</td>
                <td>${row.standing.toFixed(2)}</td>
                <td>${row.games_count}</td>
                ${placeCells}
            </tr>
        `;
    }).join('');
    return `
        <details class="stats-card awards-card podium-board" open>
            <summary class="podium-summary awards-card-header">
                <span class="podium-summary-title">🏆 The Podium</span>
                ${renderInfoBtn(PODIUM_INFO)}
            </summary>
            <p class="stats-info-tip" hidden></p>
            <div class="podium-scroll">
                <table class="awards-table podium-table">
                    <thead>
                        <tr>
                            <th class="podium-sticky-rank">#</th>
                            <th class="podium-sticky-name">Player</th>
                            <th>Standing</th>
                            <th>Games</th>
                            ${placeHeaders}
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        </details>
    `;
}

/** Wire ℹ buttons — tap toggles tip under the header. */
export function bindStatsInfoTips(root) {
    if (!root) return;
    root.querySelectorAll('.stats-info-btn').forEach((btn) => {
        btn.addEventListener('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            const card = btn.closest('.awards-card');
            const tip = card?.querySelector('.stats-info-tip');
            if (!tip) return;
            const opening = tip.hasAttribute('hidden');
            root.querySelectorAll('.stats-info-tip').forEach((el) => {
                el.setAttribute('hidden', '');
                el.textContent = '';
            });
            root.querySelectorAll('.stats-info-btn').forEach((b) => {
                b.setAttribute('aria-expanded', 'false');
            });
            if (opening) {
                tip.textContent = btn.dataset.info || '';
                tip.removeAttribute('hidden');
                btn.setAttribute('aria-expanded', 'true');
            }
        });
    });
}
