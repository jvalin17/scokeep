/**
 * ui-affordance.test.js — Accessible names and dialog layout for controls.
 *
 * Structural source tests (markup contracts). Run:
 *   npx vitest run tests/js/ui-affordance.test.js --environment node
 */

import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

// @vitest-environment node

function readSource(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8');
}

describe('test_stats_settings_dialog_close_is_labeled_and_separate', () => {
  it('stats settings dialog has a heading, labeled Close, and Edit Mode is a separate control', () => {
    const source = readSource('app/static/js/screens/stats.js');
    const css = readSource('app/static/css/style.css');

    expect(source).toMatch(/action-dialog-title|Stats settings/);
    expect(source).toMatch(/action-dialog-close[^>]*(aria-label=["']Close["']|aria-label=\{)/);
    expect(source).toMatch(/id="toggle-edit"/);
    expect(source).toMatch(/aria-label=["']Settings["']/);
    expect(source).not.toMatch(/id="stats-gear"[^>]*class="btn-refresh"/);
    expect(css).toMatch(/\.action-dialog-header/);
  });
});

describe('test_icon_only_controls_have_aria_labels', () => {
  it('home and island toggles expose aria-labels', () => {
    const screenParts = readSource('app/static/js/components/screen-parts.js');
    const scoreboard = readSource('app/static/js/screens/scoreboard.js');

    expect(screenParts).toMatch(/btn-home[^>]*aria-label=["']Back to room["']/);
    expect(scoreboard).toMatch(/btn-home[^>]*aria-label=["']Back to room["']/);
    expect(screenParts).toMatch(/island-toggle[^>]*aria-label=/);
  });
});

describe('test_home_remove_player_uses_aria_label', () => {
  it('create and quick-game remove buttons use aria-label Remove', () => {
    const home = readSource('app/static/js/screens/home.js');
    const removeButtons = home.match(/btn-remove[\s\S]{0,120}/g) || [];
    expect(removeButtons.length).toBeGreaterThanOrEqual(2);
    for (const snippet of removeButtons) {
      expect(snippet).toMatch(/aria-label=/);
      expect(snippet).not.toMatch(/title=["']Remove["']/);
    }
  });
});

describe('test_browse_close_label_is_plain_close', () => {
  it('browse toggle close copy is Close without a times glyph', () => {
    const home = readSource('app/static/js/screens/home.js');
    expect(home).toMatch(/textContent\s*=\s*['"]Close['"]/);
    expect(home).not.toMatch(/Close\s*×/);
  });
});

describe('test_howto_includes_scoresheet_section', () => {
  it('How To documents Scoresheet settings and entry flow', () => {
    const home = readSource('app/static/js/screens/home.js');
    expect(home).toContain('How to Use Scoresheet');
    for (const needle of [
      'Show totals',
      'Allow negatives',
      'Highest',
      'Lowest',
      'dialer',
      'Next Round',
      'Finished',
      'Undo Last Round',
    ]) {
      expect(home, `missing: ${needle}`).toContain(needle);
    }
  });
});

describe('test_award_info_button_aria_label', () => {
  it('award info tip button uses a descriptive aria-label', () => {
    const awards = readSource('app/static/js/components/stats-awards.js');
    expect(awards).toMatch(/aria-label=["']About this award["']/);
    expect(awards).not.toMatch(/aria-label=["']About["']/);
  });
});

describe('test_inline_edit_uses_cancel_when_editing', () => {
  it('inline edit buttons keep Edit when idle and Cancel when editing', () => {
    const bidding = readSource('app/static/js/screens/bidding.js');
    const roundend = readSource('app/static/js/screens/roundend.js');
    const review = readSource('app/static/js/screens/review.js');
    for (const source of [bidding, roundend, review]) {
      expect(source).toMatch(/isEditing \? 'Cancel' : 'Edit'/);
    }
  });
});
