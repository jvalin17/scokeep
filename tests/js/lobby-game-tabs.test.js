import { describe, it, expect } from 'vitest';
import { renderGameTypeTabs } from '../../app/static/js/components/game-settings.js';

describe('renderGameTypeTabs', () => {
  it('renders Judgement and Scoresheet tabs in a borderless tablist', () => {
    const html = renderGameTypeTabs('kachuful');
    expect(html).toContain('class="lobby-game-tabs stats-tabs"');
    expect(html).toContain('role="tablist"');
    expect(html).toContain('data-game-tab="kachuful"');
    expect(html).toContain('data-game-tab="scoresheet"');
    expect(html).toContain('Judgement');
    expect(html).toContain('Scoresheet');
    expect(html).not.toContain('setting-game-type');
  });

  it('marks the selected tab active and wires aria-controls', () => {
    const judgement = renderGameTypeTabs('kachuful');
    expect(judgement).toContain('id="game-tab-kachuful"');
    expect(judgement).toContain('id="game-tab-scoresheet"');
    expect(judgement).toContain('aria-controls="lobby-settings-host"');
    expect(judgement).toContain('data-game-tab="kachuful" aria-selected="true"');
    expect(judgement).toContain('data-game-tab="scoresheet" aria-selected="false"');

    const scoresheet = renderGameTypeTabs('scoresheet');
    expect(scoresheet).toContain('data-game-tab="scoresheet" aria-selected="true"');
    expect(scoresheet).toContain('data-game-tab="kachuful" aria-selected="false"');
  });
});
