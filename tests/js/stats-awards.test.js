/**
 * stats-awards.test.js — Awards / Podium render helpers.
 * Fixtures are synthetic (factory).
 * Run with: npx vitest run tests/js/stats-awards.test.js
 */

import { describe, it, expect } from 'vitest';
import {
  renderPodiumBoard,
  renderCareerTable,
  bindStatsInfoTips,
} from '../../app/static/js/components/stats-awards.js';

describe('renderPodiumBoard', () => {
  const podium = [
    { player: 'Lala', standing: 4.2, games_count: 23, places: { 1: 6, 2: 7, 3: 8, 4: 1, 5: 1 } },
    { player: 'Anjum', standing: 3.72, games_count: 23, places: { 1: 3, 2: 7, 3: 4, 4: 3, 5: 6 } },
  ];

  it('has no leader summary line', () => {
    const html = renderPodiumBoard(podium);
    expect(html).not.toMatch(/leads/);
    expect(html).not.toMatch(/5 players/);
    expect(html).not.toMatch(/4\.20 ·/);
  });

  it('hides formula behind an info button instead of a paragraph', () => {
    const html = renderPodiumBoard(podium);
    expect(html).toContain('stats-info-btn');
    expect(html).toContain('Weighted finishes');
    expect(html).not.toMatch(/<p class="stats-muted podium-desc"/);
  });

  it('wraps table in podium-scroll for card containment', () => {
    const html = renderPodiumBoard(podium);
    expect(html).toContain('class="podium-scroll"');
    expect(html).toContain('podium-table');
    expect(html.indexOf('podium-scroll')).toBeLessThan(html.indexOf('podium-table'));
  });

  it('returns empty string for empty podium', () => {
    expect(renderPodiumBoard([])).toBe('');
    expect(renderPodiumBoard(null)).toBe('');
  });
});

describe('renderCareerTable', () => {
  it('puts description on info button not a subtitle paragraph', () => {
    const html = renderCareerTable(
      'Sniper',
      '🎯',
      'Bid exactly 1 and made it',
      [{ name: 'Jj', count: 12 }],
    );
    expect(html).toContain('stats-info-btn');
    expect(html).toContain('Bid exactly 1 and made it');
    expect(html).not.toMatch(/<p class="stats-muted"/);
  });
});

describe('bindStatsInfoTips', () => {
  it('toggles tip text on info button click', () => {
    document.body.innerHTML = `
      <div class="awards-card">
        <button type="button" class="stats-info-btn" data-info="Hello tip" aria-expanded="false">ℹ</button>
        <p class="stats-info-tip" hidden></p>
      </div>
    `;
    bindStatsInfoTips(document.body);
    const btn = document.querySelector('.stats-info-btn');
    const tip = document.querySelector('.stats-info-tip');
    btn.click();
    expect(tip.hasAttribute('hidden')).toBe(false);
    expect(tip.textContent).toBe('Hello tip');
    btn.click();
    expect(tip.hasAttribute('hidden')).toBe(true);
  });
});
