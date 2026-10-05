import { describe, it, expect } from 'vitest';
import { buildPlaygroundStatsPath } from '../../app/static/js/api.js';

describe('buildPlaygroundStatsPath', () => {
  it('builds stats URL with game_type and pagination', () => {
    expect(buildPlaygroundStatsPath('ABCD')).toBe('/playground/ABCD/stats');
    expect(buildPlaygroundStatsPath('ABCD', { gameType: 'all' })).toBe(
      '/playground/ABCD/stats?game_type=all',
    );
    expect(buildPlaygroundStatsPath('ABCD', { gameType: 'scoresheet' })).toBe(
      '/playground/ABCD/stats?game_type=scoresheet',
    );
    expect(buildPlaygroundStatsPath('ABCD', { gameType: 'kachuful', offset: 40, limit: 20 })).toBe(
      '/playground/ABCD/stats?offset=40&limit=20&game_type=kachuful',
    );
  });
});
