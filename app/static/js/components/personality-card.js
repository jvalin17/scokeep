// Personality card component — flippable cards with avatar, insights, accuracy chart
// Personality metadata served from API (Python is single source of truth)

import { escapeHtml } from './game-utils.js';

const FALLBACK_META = { name: 'Unknown', tagline: '', color: '#37474F', icon: '❓' };

export function renderPersonalityCards(players) {
    const names = Object.keys(players);
    if (!names.length) {
        return '<p class="stats-empty">No player data yet.</p>';
    }

    const cards = names.map(name => renderSingleCard(name, players[name])).join('');

    return `
        <div class="personality-list">
            ${cards}
        </div>
    `;
}

function renderSingleCard(playerName, data) {
    if (!data.personality) {
        return renderLockedCard(playerName, data);
    }

    const meta = data.meta || FALLBACK_META;

    return `
        <div class="personality-card" style="--card-color: ${meta.color}">
            <div class="personality-card-inner">
                ${renderCardFront(playerName, data, meta)}
                ${renderCardBack(playerName, data)}
            </div>
        </div>
    `;
}

function renderLockedCard(playerName, data) {
    const progress = data.games_analyzed || 0;
    const needed = data.unlock_at || 3;
    const pct = Math.round((progress / needed) * 100);

    return `
        <div class="personality-card personality-card-locked">
            <div class="personality-card-inner">
                <div class="personality-front">
                    <div class="personality-icon" style="font-size: 3rem; opacity: 0.3;">🔒</div>
                    <div class="personality-name">${escapeHtml(playerName)}</div>
                    <div class="personality-tagline">Personality unlocking...</div>
                    <div class="personality-unlock-bar">
                        <div class="personality-unlock-fill" style="width: ${pct}%"></div>
                    </div>
                    <div class="personality-unlock-text">${progress}/${needed} games</div>
                </div>
            </div>
        </div>
    `;
}

function renderCardFront(playerName, data, meta) {
    const overallAccuracy = computeOverallAccuracy(data.accuracy_by_cards);

    return `
        <div class="personality-front">
            <div class="personality-badge" title="Based on all games played">ℹ overall insights</div>
            <div class="personality-icon">${meta.icon}</div>
            <div class="personality-type">${meta.name}</div>
            <div class="personality-tagline">${meta.tagline}</div>
            ${overallAccuracy !== null ? renderAccuracyDial(overallAccuracy) : ''}
            <div class="personality-player-name">${escapeHtml(playerName)}</div>
            <div class="personality-flip-hint">tap to flip</div>
        </div>
    `;
}

function computeOverallAccuracy(accuracyByCards) {
    if (!accuracyByCards) return null;
    let totalCorrect = 0;
    let totalRounds = 0;
    for (const data of Object.values(accuracyByCards)) {
        totalRounds += data.rounds;
        totalCorrect += Math.round(data.pct / 100 * data.rounds);
    }
    if (totalRounds === 0) return null;
    return Math.round(totalCorrect / totalRounds * 100);
}

function renderAccuracyDial(pct) {
    // SVG ring dial — 0-100%
    const radius = 28;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (pct / 100) * circumference;

    return `
        <div class="accuracy-dial">
            <svg width="70" height="70" viewBox="0 0 70 70">
                <circle cx="35" cy="35" r="${radius}" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="5"/>
                <circle cx="35" cy="35" r="${radius}" fill="none" stroke="rgba(255,255,255,0.85)" stroke-width="5"
                    stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"
                    stroke-linecap="round" transform="rotate(-90 35 35)"/>
                <text x="35" y="38" text-anchor="middle" fill="white" font-size="14" font-weight="700">${pct}%</text>
            </svg>
            <div class="accuracy-dial-label">Accuracy</div>
        </div>
    `;
}

function renderCardBack(playerName, data) {
    const accuracy = data.accuracy_by_cards || {};
    const insights = data.insights || [];
    const extras = data.extras || {};
    const gamesAnalyzed = data.games_analyzed || 0;
    const overallAccuracy = computeOverallAccuracy(accuracy);

    const previousNote = data.previous_personality
        ? `<div class="personality-evolution">Evolved from ${escapeHtml(data.previous_personality)}</div>`
        : '';

    return `
        <div class="personality-back">
            ${renderTopBar(overallAccuracy, extras)}
            ${renderAccuracyChart(accuracy)}
            ${renderStatsTable(extras)}

            <div class="personality-insights">
                ${insights[0] ? `<div class="insight-strength">💡 ${escapeHtml(insights[0])}</div>` : ''}
                ${insights[1] ? `<div class="insight-growth">🌱 ${escapeHtml(insights[1])}</div>` : ''}
            </div>

            ${renderFunFacts(extras.fun_facts)}

            <div class="personality-meta">
                <span>${gamesAnalyzed} games · ${extras.total_rounds || 0} rounds</span>
                <span>${renderTrendBadge(extras.trend)}</span>
            </div>
            ${previousNote}
            <div class="personality-flip-hint">tap to flip</div>
        </div>
    `;
}

function renderTopBar(overallAccuracy, extras) {
    const winsText = extras.wins !== undefined
        ? `<span class="top-bar-wins">${extras.wins}/${extras.games_played} W</span>`
        : '';

    const dialHtml = overallAccuracy !== null
        ? renderAccuracyDialSmall(overallAccuracy)
        : '';

    return `<div class="card-top-bar">${dialHtml}${winsText}</div>`;
}

function renderAccuracyDialSmall(pct) {
    const radius = 18;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (pct / 100) * circumference;

    return `
        <div class="accuracy-dial-small">
            <svg width="46" height="46" viewBox="0 0 46 46">
                <circle cx="23" cy="23" r="${radius}" fill="none" stroke="#eee" stroke-width="4"/>
                <circle cx="23" cy="23" r="${radius}" fill="none" stroke="#43A047" stroke-width="4"
                    stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"
                    stroke-linecap="round" transform="rotate(-90 23 23)"/>
                <text x="23" y="27" text-anchor="middle" fill="#333" font-size="11" font-weight="700">${pct}%</text>
            </svg>
        </div>
    `;
}

function renderStatsTable(extras) {
    const rows = [];

    // Bidding style
    if (extras.bidding_style) {
        const styleLabel = extras.bidding_style === 'aggressive' ? 'Aggressive'
            : extras.bidding_style === 'conservative' ? 'Conservative' : 'Balanced';
        rows.push(['Style', styleLabel]);
    }

    // Clutch
    if (extras.clutch_opportunities > 0) {
        const clutchPct = Math.round(extras.clutch_wins / extras.clutch_opportunities * 100);
        rows.push(['Clutch', `${extras.clutch_wins}/${extras.clutch_opportunities} (${clutchPct}%)`]);
    }

    // Zero bids
    if (extras.zero_bid_rate > 0) {
        rows.push(['Zero bids', `${extras.zero_bid_rate}% success`]);
    }

    // Best suit
    if (extras.best_trump) {
        const isRed = extras.best_trump === '♦' || extras.best_trump === '♥';
        const suitHtml = isRed
            ? `<span style="color:#D32F2F;">${extras.best_trump}</span>`
            : `<span>${extras.best_trump}</span>`;
        rows.push(['Best suit', `${suitHtml} ${extras.best_trump_pct}%`]);
    }

    // Tempo
    if (extras.tempo && extras.tempo !== 'even') {
        const tempoLabel = extras.tempo === '1st half' ? '1st half player' : '2nd half player';
        rows.push(['Tempo', tempoLabel]);
    }

    // Favorite bid
    if (extras.favorite_bid !== null && extras.favorite_bid !== undefined) {
        rows.push(['Fav bid', extras.favorite_bid]);
    }

    // Best round
    if (extras.biggest_round_score > 0) {
        rows.push(['Best round', `+${extras.biggest_round_score}`]);
    }

    // Consistency
    if (extras.consistency) {
        rows.push(['Consistency', extras.consistency === 'high' ? 'Reliable'
            : extras.consistency === 'medium' ? 'Mixed' : 'Unpredictable']);
    }

    if (!rows.length) return '';

    return `
        <div class="stats-table-compact">
            ${rows.map(([label, value]) => `
                <div class="stats-table-row">
                    <span class="stats-table-label">${label}</span>
                    <span class="stats-table-value">${value}</span>
                </div>
            `).join('')}
        </div>
    `;
}

function renderTrendBadge(trend) {
    if (trend === 'improving') return '<span class="trend-badge trend-up">↑ Improving</span>';
    if (trend === 'declining') return '<span class="trend-badge trend-down">↓ Cooling off</span>';
    return '<span class="trend-badge trend-steady">→ Steady</span>';
}

function renderFunFacts(facts) {
    if (!facts || !facts.length) {
        return '<div class="fun-facts"><div class="fun-fact stats-muted">Keep playing to unlock fun facts</div></div>';
    }
    return `
        <div class="fun-facts">
            ${facts.map(f => `<div class="fun-fact">⚡ ${escapeHtml(f)}</div>`).join('')}
        </div>
    `;
}

function renderAccuracyChart(accuracy) {
    if (!accuracy || typeof accuracy !== 'object') {
        return '<div class="stats-muted" style="padding: 8px 0;">No accuracy data yet</div>';
    }
    const cardCounts = Object.keys(accuracy)
        .map(Number)
        .sort((a, b) => b - a);

    if (!cardCounts.length) {
        return '<div class="stats-muted" style="padding: 8px 0;">No accuracy data yet</div>';
    }

    return `
        <div class="accuracy-chart">
            ${cardCounts.map(cards => {
                const data = accuracy[String(cards)];
                const pct = data.pct;
                const rounds = data.rounds;
                return `
                    <div class="accuracy-row">
                        <span class="accuracy-label">${cards}</span>
                        <div class="accuracy-bar-track">
                            <div class="accuracy-bar-fill" style="width: ${pct}%"></div>
                        </div>
                        <span class="accuracy-value">${pct}%</span>
                        <span class="accuracy-rounds">(${rounds})</span>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}
