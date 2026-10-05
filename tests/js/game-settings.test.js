/**
 * Tests for game-settings.js — shared settings grid component.
 *
 * Verifies that renderSettingsGrid produces correct HTML for all 6 settings,
 * readSettings extracts values from the DOM, and updateCardsDropdown adjusts
 * the cards-per-round dropdown when player count changes.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import {
  renderSettingsGrid,
  readSettings,
  updateCardsDropdown,
  bindToggleLabels,
} from '../../app/static/js/components/game-settings.js';

describe('renderSettingsGrid', () => {
  it('returns HTML with all 6 settings', () => {
    const html = renderSettingsGrid({ prefix: 'test', playerCount: 3 });
    expect(html).toContain('id="test-mode"');
    expect(html).toContain('id="test-appearance"');
    expect(html).toContain('id="test-cards"');
    expect(html).toContain('id="test-scoring"');
    expect(html).toContain('id="test-sets"');
    expect(html).toContain('id="test-must-lose"');
  });

  it('computes max cards from player count', () => {
    // 4 players → floor(52/4) = 13 max cards
    const html = renderSettingsGrid({ prefix: 'x', playerCount: 4 });
    expect(html).toContain('value="13"');
    expect(html).not.toContain('value="14"');
  });

  it('defaults selected cards to min maxCards 8', () => {
    // 3 players → floor(52/3) = 17. Selected should be 8.
    const html = renderSettingsGrid({ prefix: 'x', playerCount: 3 });
    expect(html).toContain('value="8" selected');
  });

  it('uses 2 as minimum player count for max cards', () => {
    // 0 players should not cause division issues — uses max(0, 2) = 2
    const html = renderSettingsGrid({ prefix: 'x', playerCount: 0 });
    expect(html).toContain('value="26"'); // floor(52/2) = 26
  });

  it('renders Scoresheet settings when gameType is scoresheet', () => {
    const html = renderSettingsGrid({ prefix: 'ss', playerCount: 3, gameType: 'scoresheet' });
    expect(html).toContain('data-game-settings="scoresheet"');
    expect(html).toContain('id="ss-winner"');
    expect(html).toContain('id="ss-show-totals"');
    expect(html).toContain('id="ss-allow-negatives"');
    expect(html).toContain('id="ss-label"');
    expect(html).toContain('Navy (off-white)');
    expect(html).not.toContain('id="ss-mode"');
  });
});


describe('readSettings', () => {
  let container;

  beforeEach(() => {
    container = document.createElement('div');
    container.innerHTML = renderSettingsGrid({ prefix: 'test', playerCount: 3 });
    document.body.innerHTML = '';
    document.body.appendChild(container);
  });

  it('reads settings values from the DOM', () => {
    // Set values explicitly (happy-dom doesn't reliably handle `selected` attr)
    container.querySelector('#test-mode').value = 'rookie';
    container.querySelector('#test-appearance').value = 'interactive';
    container.querySelector('#test-scoring').value = 'kachuful_standard';
    container.querySelector('#test-sets').value = '3';
    container.querySelector('#test-cards').value = '8';
    container.querySelector('#test-must-lose').checked = true;

    const settings = readSettings(container, 'test');
    expect(settings.mode).toBe('rookie');
    expect(settings.appearance).toBe('interactive');
    expect(settings.scoring_formula).toBe('kachuful_standard');
    expect(settings.num_sets).toBe(3);
    expect(settings.rounds_per_set).toBe(8);
    expect(settings.must_lose).toBe(true);
  });

  it('reads changed values', () => {
    container.querySelector('#test-mode').value = 'expert';
    container.querySelector('#test-sets').value = '5';
    container.querySelector('#test-must-lose').checked = false;

    const settings = readSettings(container, 'test');
    expect(settings.mode).toBe('expert');
    expect(settings.num_sets).toBe(5);
    expect(settings.must_lose).toBe(false);
  });

  it('reads Scoresheet settings from the DOM', () => {
    container.innerHTML = renderSettingsGrid({
      prefix: 'test',
      playerCount: 3,
      gameType: 'scoresheet',
    });
    container.querySelector('#test-label').value = 'Declare';
    container.querySelector('#test-winner').value = 'lowest';
    container.querySelector('#test-show-totals').checked = false;
    container.querySelector('#test-allow-negatives').checked = true;

    const settings = readSettings(container, 'test', 'scoresheet');
    expect(settings.game_type).toBe('scoresheet');
    expect(settings.label).toBe('Declare');
    expect(settings.winner).toBe('lowest');
    expect(settings.show_totals).toBe(false);
    expect(settings.allow_negatives).toBe(true);
  });
});

describe('bindToggleLabels', () => {
  it('updates Allow negatives label from Off to On when checked', () => {
    const container = document.createElement('div');
    container.innerHTML = renderSettingsGrid({
      prefix: 'test',
      playerCount: 3,
      gameType: 'scoresheet',
    });
    document.body.innerHTML = '';
    document.body.appendChild(container);

    bindToggleLabels(container);
    const checkbox = container.querySelector('#test-allow-negatives');
    const label = checkbox.parentElement.querySelector('.toggle-label');
    expect(label.textContent).toBe('Off');

    checkbox.checked = true;
    checkbox.dispatchEvent(new Event('change', { bubbles: true }));
    expect(label.textContent).toBe('On');
  });
});

describe('updateCardsDropdown', () => {
  let container;

  beforeEach(() => {
    container = document.createElement('div');
    container.innerHTML = renderSettingsGrid({ prefix: 'up', playerCount: 3 });
    document.body.innerHTML = '';
    document.body.appendChild(container);
  });

  it('adjusts max cards when player count changes', () => {
    // 7 players → floor(52/7) = 7
    updateCardsDropdown(container, 'up', 7);
    const options = container.querySelectorAll('#up-cards option');
    expect(options.length).toBe(7);
    expect(options[0].value).toBe('7');
  });

  it('clamps selected value to new max', () => {
    // Set current to 8, then change to 7 players (max=7) → should clamp to 7
    container.querySelector('#up-cards').value = '8';
    updateCardsDropdown(container, 'up', 7);
    expect(container.querySelector('#up-cards').value).toBe('7');
  });
});

describe('scoresheet label field', () => {
  it('caps label input at 80 characters', () => {
    const html = renderSettingsGrid({ prefix: 'setting', playerCount: 2, gameType: 'scoresheet' });
    expect(html).toMatch(/id="setting-label"[^>]*maxlength="80"/);
  });
});

