// Career awards + last game awards rendering for stats screen

import { escapeHtml } from './game-utils.js';

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
        <div class="stats-card" style="margin-bottom:16px;padding:12px;">
            <h4 style="margin:0 0 4px;">${emoji} ${title}</h4>
            <p class="stats-muted" style="font-size:0.75rem;margin-bottom:8px;">${description}</p>
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
            <div class="stats-card" style="margin-bottom:8px;padding:10px 12px;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span>${escapeHtml(t.emoji)} ${escapeHtml(t.title)}</span>
                    <strong style="margin-left:8px;">${escapeHtml(t.player)}</strong>
                </div>
                <div class="stats-muted" style="margin-top:2px;font-size:0.7rem;">${escapeHtml(t.desc)}</div>
                <div class="stats-muted" style="margin-top:2px;font-size:0.8rem;">
                    ${escapeHtml(t.detail)}
                </div>
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
                <div class="stats-card" style="margin-bottom:8px;padding:10px 12px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span>${a.emoji} ${a.title}</span>
                        <strong style="margin-left:8px;">${escapeHtml(data.name)}</strong>
                    </div>
                    <div class="stats-muted" style="margin-top:2px;font-size:0.7rem;">${a.desc}</div>
                    <div class="stats-muted" style="margin-top:2px;font-size:0.8rem;">
                        ${escapeHtml(a.detail(data))}
                    </div>
                </div>
            `;
        }).join('');
    return `
        <h3 style="margin-bottom:12px;">Last Game</h3>
        ${cards}
    `;
}
