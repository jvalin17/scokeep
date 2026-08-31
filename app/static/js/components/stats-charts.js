// Score progression chart + game detail scoresheet for stats screen

import { getTrump, escapeHtml } from './game-utils.js';

const CHART_COLORS = ['#E53935', '#1E88E5', '#43A047', '#FB8C00', '#8E24AA', '#00ACC1'];

function buildCumulativeTotals(players, rounds) {
    const cumulative = players.map(() => [0]);
    for (const round of rounds) {
        players.forEach((_, idx) => {
            const prev = cumulative[idx][cumulative[idx].length - 1];
            cumulative[idx].push(prev + (round.scores[String(idx)] || 0));
        });
    }
    return cumulative;
}

export function renderScoreChart(players, rounds) {
    const cumulative = buildCumulativeTotals(players, rounds);
    const allValues = cumulative.flat();
    const minVal = Math.min(...allValues);
    const maxVal = Math.max(...allValues);
    const range = maxVal - minVal || 1;

    const W = 300, H = 180, PAD_L = 35, PAD_R = 10, PAD_T = 15, PAD_B = 25;
    const plotW = W - PAD_L - PAD_R;
    const plotH = H - PAD_T - PAD_B;
    const totalPts = rounds.length + 1;

    const x = i => PAD_L + (i / (totalPts - 1)) * plotW;
    const y = v => PAD_T + plotH - ((v - minVal) / range) * plotH;

    // Y-axis gridlines
    const gridCount = 4;
    const gridStep = range / gridCount;
    let gridLines = '';
    for (let i = 0; i <= gridCount; i++) {
        const val = minVal + gridStep * i;
        const yy = y(val);
        gridLines += `<line x1="${PAD_L}" y1="${yy}" x2="${W - PAD_R}" y2="${yy}" stroke="#e0e0e0" stroke-width="0.5"/>`;
        gridLines += `<text x="${PAD_L - 4}" y="${yy + 3}" text-anchor="end" fill="#999" font-size="8">${Math.round(val)}</text>`;
    }

    // X-axis labels (every 8 rounds for set boundaries)
    let xLabels = '';
    for (let i = 0; i < totalPts; i++) {
        if (i === 0 || i % 8 === 0 || i === totalPts - 1) {
            xLabels += `<text x="${x(i)}" y="${H - 4}" text-anchor="middle" fill="#999" font-size="8">${i}</text>`;
        }
    }

    // Zero line
    let zeroLine = '';
    if (minVal < 0 && maxVal > 0) {
        zeroLine = `<line x1="${PAD_L}" y1="${y(0)}" x2="${W - PAD_R}" y2="${y(0)}" stroke="#bbb" stroke-width="0.8" stroke-dasharray="3,2"/>`;
    }

    // Player lines + end dots
    let lines = '';
    let dots = '';
    cumulative.forEach((data, idx) => {
        const color = CHART_COLORS[idx % CHART_COLORS.length];
        const points = data.map((v, i) => `${x(i)},${y(v)}`).join(' ');
        lines += `<polyline points="${points}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round"/>`;
        const lastX = x(data.length - 1), lastY = y(data[data.length - 1]);
        dots += `<circle cx="${lastX}" cy="${lastY}" r="3" fill="${color}"/>`;
    });

    // Legend
    const legend = players.map((name, idx) => {
        const color = CHART_COLORS[idx % CHART_COLORS.length];
        return `<span style="display:inline-flex;align-items:center;gap:3px;margin-right:8px;font-size:11px;">
            <span style="width:10px;height:3px;background:${color};display:inline-block;border-radius:1px;"></span>${escapeHtml(name)}
        </span>`;
    }).join('');

    return `
        <div class="score-chart" style="margin:8px 0;">
            <div style="text-align:center;margin-bottom:4px;">${legend}</div>
            <svg viewBox="0 0 ${W} ${H}" style="width:100%;max-width:500px;display:block;margin:0 auto;">
                ${gridLines}${zeroLine}${xLabels}${lines}${dots}
            </svg>
        </div>
    `;
}

export function renderGameDetail(game, scoreboard, editMode) {
    const players = game.players;
    const rounds = scoreboard.rounds;
    const totals = scoreboard.totals;
    if (!rounds.length) return '<p class="stats-muted" style="padding:8px;">No round data</p>';

    return `
        <div class="game-detail">
            ${renderScoreChart(players, rounds)}
            <div class="game-detail-legend">
                <span class="legend-item"><span class="legend-swatch legend-overbid"></span> Overbid</span>
                <span class="legend-item"><span class="legend-swatch legend-underbid"></span> Underbid</span>
            </div>
            <div class="score-table-full" style="margin-top:8px;">
                <table class="scoresheet">
                    <thead>
                        <tr>
                            <th>R#</th>
                            ${players.map(name => `<th>${escapeHtml(name)}</th>`).join('')}
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
                                    return `<td class="score-cell ${cellClass} ${score < 0 ? 'score-negative' : ''}"
                                        data-game-id="${game.game_id}" data-round="${round.round_num}" data-player="${idx}" data-score="${score}">
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
