/**
 * Resume Game visibility is scoped to the selected game-type tab.
 */
import { describe, it, expect } from 'vitest';
import {
  shouldShowResumeForTab,
  initialGameTypeForLobby,
  renderResumeBlock,
} from '../../app/static/js/screens/lobby-resume.js';

describe('shouldShowResumeForTab', () => {
  it('hides resume when there is no active game', () => {
    expect(shouldShowResumeForTab(null, 'kachuful')).toBe(false);
    expect(shouldShowResumeForTab(undefined, 'scoresheet')).toBe(false);
  });

  it('shows resume only when tab matches active game_type', () => {
    const judgement = { settings: { game_type: 'kachuful' } };
    const scoresheet = { settings: { game_type: 'scoresheet' } };

    expect(shouldShowResumeForTab(judgement, 'kachuful')).toBe(true);
    expect(shouldShowResumeForTab(judgement, 'scoresheet')).toBe(false);
    expect(shouldShowResumeForTab(scoresheet, 'scoresheet')).toBe(true);
    expect(shouldShowResumeForTab(scoresheet, 'kachuful')).toBe(false);
  });

  it('treats missing game_type as judgement (kachuful)', () => {
    expect(shouldShowResumeForTab({ settings: {} }, 'kachuful')).toBe(true);
    expect(shouldShowResumeForTab({ settings: {} }, 'scoresheet')).toBe(false);
  });
});

describe('initialGameTypeForLobby', () => {
  it('selects the active game tab on load', () => {
    expect(initialGameTypeForLobby({ settings: { game_type: 'scoresheet' } })).toBe(
      'scoresheet',
    );
    expect(initialGameTypeForLobby({ settings: { game_type: 'kachuful' } })).toBe(
      'kachuful',
    );
    expect(initialGameTypeForLobby(null)).toBe('kachuful');
  });
});

describe('renderResumeBlock', () => {
  it('renders Resume markup only for the matching tab', () => {
    const active = { current_round: 3, settings: { game_type: 'scoresheet' } };
    const onTab = renderResumeBlock(active, 'scoresheet');
    expect(onTab).toContain('id="resume-game"');
    expect(onTab).toContain('Round 3');
    expect(renderResumeBlock(active, 'kachuful')).toBe('');
  });
});
