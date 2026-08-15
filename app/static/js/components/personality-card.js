// Personality card component — flippable cards with avatar, insights, accuracy chart

const PERSONALITY_META = {
    sniper:       { name: 'The Sniper',       tagline: 'Calls the shot. Makes the shot.', color: '#1B5E20', icon: '🎯' },
    gambler:      { name: 'The Gambler',      tagline: 'Goes big. Sometimes it pays off.', color: '#E65100', icon: '🎲' },
    phoenix:      { name: 'The Phoenix',      tagline: 'Slow start? That\'s the plan.', color: '#BF360C', icon: '🔥' },
    rock:         { name: 'The Rock',         tagline: 'Steady hands. No surprises.', color: '#37474F', icon: '🪨' },
    sprinter:     { name: 'The Sprinter',     tagline: 'Out of the gate like lightning.', color: '#0D47A1', icon: '⚡' },
    ghost:        { name: 'The Ghost',        tagline: 'Bids nothing. Wins everything.', color: '#4A148C', icon: '👻' },
    architect:    { name: 'The Architect',    tagline: 'Give them more cards, they build more.', color: '#006064', icon: '🏗️' },
    minimalist:   { name: 'The Minimalist',   tagline: 'Less is more. Always.', color: '#3E2723', icon: '✨' },
    comeback_kid: { name: 'The Comeback Kid', tagline: 'Don\'t count them out.', color: '#880E4F', icon: '🦅' },
    wildcard:     { name: 'The Wildcard',     tagline: 'You never know what you\'re gonna get.', color: '#FF6F00', icon: '🃏' },
};

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

    const meta = PERSONALITY_META[data.personality] || PERSONALITY_META.rock;

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
                    <div class="personality-name">${playerName}</div>
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
    return `
        <div class="personality-front">
            <div class="personality-badge" title="Based on all games played">ℹ overall insights</div>
            <div class="personality-icon">${meta.icon}</div>
            <div class="personality-type">${meta.name}</div>
            <div class="personality-tagline">${meta.tagline}</div>
            <div class="personality-player-name">${playerName}</div>
            <div class="personality-flip-hint">tap to flip</div>
        </div>
    `;
}

function renderCardBack(playerName, data) {
    const accuracy = data.accuracy_by_cards || {};
    const insights = data.insights || [];
    const extras = data.extras || {};
    const gamesAnalyzed = data.games_analyzed || 0;

    const previousNote = data.previous_personality
        ? `<div class="personality-evolution">Evolved from ${PERSONALITY_META[data.previous_personality]?.name || data.previous_personality}</div>`
        : '';

    return `
        <div class="personality-back">
            ${renderQuickStats(data, extras)}
            ${renderAccuracyChart(accuracy)}

            <div class="personality-insights">
                ${insights[0] ? `<div class="insight-strength">💡 ${insights[0]}</div>` : ''}
                ${insights[1] ? `<div class="insight-growth">🌱 ${insights[1]}</div>` : ''}
            </div>

            ${renderExtras(data, extras)}

            <div class="personality-meta">
                <span>${gamesAnalyzed} games · ${extras.total_rounds || 0} rounds</span>
                <span>${renderTrendBadge(extras.trend)}</span>
            </div>
            ${previousNote}
            ${renderFunFacts(extras.fun_facts)}
            <div class="personality-flip-hint">tap to flip</div>
        </div>
    `;
}

function renderQuickStats(data, extras) {
    const items = [];
    if (extras.wins !== undefined) {
        items.push(`<div class="quick-stat"><span class="quick-stat-value">${extras.wins}/${extras.games_played}</span><span class="quick-stat-label">Wins</span></div>`);
    }
    if (data.signature_round) {
        items.push(`<div class="quick-stat"><span class="quick-stat-value">${data.signature_round} cards</span><span class="quick-stat-label">Best at</span></div>`);
    }
    if (extras.best_trump) {
        const isRed = extras.best_trump === '♦' || extras.best_trump === '♥';
        const suitColor = isRed ? 'color:#D32F2F;' : 'color:#222;';
        items.push(`<div class="quick-stat"><span class="quick-stat-value"><span style="${suitColor}">${extras.best_trump}</span> ${extras.best_trump_pct}%</span><span class="quick-stat-label">Best suit</span></div>`);
    }
    if (extras.biggest_round_score > 0) {
        items.push(`<div class="quick-stat"><span class="quick-stat-value">+${extras.biggest_round_score}</span><span class="quick-stat-label">Best round</span></div>`);
    }
    if (!items.length) return '';
    return `<div class="quick-stats-row">${items.join('')}</div>`;
}

function renderExtras(data, extras) {
    const chips = [];
    if (extras.favorite_bid !== null && extras.favorite_bid !== undefined) {
        chips.push(`<span class="insight-chip">Favorite bid: ${extras.favorite_bid}</span>`);
    }
    if (data.kryptonite) {
        chips.push(`<span class="insight-chip insight-chip-warn">Weakest: ${data.kryptonite} cards</span>`);
    }
    if (!chips.length) return '';
    return `<div class="insight-chips">${chips.join('')}</div>`;
}

function renderTrendBadge(trend) {
    if (trend === 'improving') return '<span class="trend-badge trend-up">↑ Improving</span>';
    if (trend === 'declining') return '<span class="trend-badge trend-down">↓ Cooling off</span>';
    return '<span class="trend-badge trend-steady">→ Steady</span>';
}

function renderFunFacts(facts) {
    if (!facts || !facts.length) return '';
    return `
        <div class="fun-facts">
            ${facts.map(f => `<div class="fun-fact">⚡ ${f}</div>`).join('')}
        </div>
    `;
}

function renderAccuracyChart(accuracy) {
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
