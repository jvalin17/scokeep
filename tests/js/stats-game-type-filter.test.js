/**
 * Stats screen game-type filter tabs — markup + navigate on switch.
 * Run: npx vitest run tests/js/stats-game-type-filter.test.js
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

const getPlaygroundStats = vi.fn();

vi.mock('../../app/static/js/api.js', () => ({
  getPlaygroundStats: (...args) => getPlaygroundStats(...args),
  clearPlaygroundStats: vi.fn(),
  getScoreboard: vi.fn(),
}));

vi.mock('../../app/static/js/components/confirm-dialog.js', () => ({
  showPromptDialog: vi.fn(),
}));

vi.mock('../../app/static/js/components/personality-card.js', () => ({
  renderPersonalityCards: () => '',
}));

vi.mock('../../app/static/js/components/stats-awards.js', () => ({
  renderCareerTable: () => '',
  renderLastGameAwards: () => '',
  renderPodiumBoard: () => '',
  bindStatsInfoTips: () => {},
}));

vi.mock('../../app/static/js/components/stats-charts.js', () => ({
  renderGameDetail: () => '',
}));

import { statsScreen } from '../../app/static/js/screens/stats.js';

beforeEach(() => {
  getPlaygroundStats.mockReset();
  getPlaygroundStats.mockResolvedValue({
    total_games: 1,
    game_history: [{ id: 1, game_type: 'kachuful', label: null }],
    highlights: null,
    insights: null,
  });
  sessionStorage.clear();
});

describe('stats game-type filter', () => {
  it('renders filter and switches via navigate', async () => {
    const container = document.createElement('div');
    document.body.appendChild(container);
    const navigate = vi.fn();

    await statsScreen.mount(container, {}, {
      navigate,
      params: ['ABCD', 'all'],
    });

    expect(getPlaygroundStats).toHaveBeenCalledWith('ABCD', { gameType: 'all' });
    expect(container.querySelector('[role="tablist"][aria-label="Stats game type"]')).toBeTruthy();
    expect(container.querySelector('[data-game-type-filter="all"]')?.getAttribute('aria-selected')).toBe('true');
    expect(container.querySelector('[data-game-type-filter="kachuful"]')).toBeTruthy();
    expect(container.querySelector('[data-game-type-filter="scoresheet"]')).toBeTruthy();

    container.querySelector('[data-game-type-filter="scoresheet"]').click();
    expect(navigate).toHaveBeenCalledWith('stats/ABCD/scoresheet');

    container.remove();
  });
});
