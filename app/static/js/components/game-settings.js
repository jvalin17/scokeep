/**
 * game-settings.js — Shared settings grid for game configuration.
 *
 * Used by both lobby (online games) and home screen (Quick Game).
 * Renders identical settings UI with configurable ID prefix to avoid collisions.
 *
 * Settings: Mode, Appearance, Cards per round, Scoring, Sets, Must-lose.
 * Source: requirements/quick-game.md line 54 — "Same settings UI as lobby".
 */

/**
 * Compute the maximum cards per round for a given player count.
 * @param {number} playerCount
 * @returns {number}
 */
function maxCardsForPlayers(playerCount) {
  return Math.floor(52 / Math.max(playerCount, 2));
}

/**
 * Render the cards-per-round <option> elements.
 * @param {number} maxCards
 * @param {number} selected — which value to pre-select
 * @returns {string} HTML option elements
 */
function renderCardsOptions(maxCards, selected) {
  return Array.from({ length: maxCards }, (_, i) => maxCards - i)
    .map(n => `<option value="${n}" ${n === selected ? 'selected' : ''}>${n} card${n > 1 ? 's' : ''}</option>`)
    .join('');
}

/**
 * Lobby game-type tabs — Judgement vs Scoresheet (no dropdown).
 *
 * @param {'kachuful'|'scoresheet'|string} selected
 * @returns {string} HTML string
 */
export function renderGameTypeTabs(selected = 'kachuful') {
  const judgementActive = selected === 'kachuful' ? ' active' : '';
  const scoresheetActive = selected === 'scoresheet' ? ' active' : '';
  return `
    <div class="lobby-game-tabs stats-tabs" role="tablist" aria-label="Game type">
      <button type="button" role="tab" id="game-tab-kachuful" class="stats-tab${judgementActive}"
        data-game-tab="kachuful" aria-selected="${selected === 'kachuful'}"
        aria-controls="lobby-settings-host">Judgement</button>
      <button type="button" role="tab" id="game-tab-scoresheet" class="stats-tab${scoresheetActive}"
        data-game-tab="scoresheet" aria-selected="${selected === 'scoresheet'}"
        aria-controls="lobby-settings-host">Scoresheet</button>
    </div>
  `;
}

/**
 * Render the full settings grid HTML.
 *
 * @param {Object} options
 * @param {string} options.prefix — ID prefix (e.g. 'setting', 'quick-setting')
 * @param {number} options.playerCount — number of players (for max cards calculation)
 * @param {string} [options.gameType='kachuful'] — kachuful | scoresheet
 * @returns {string} HTML string
 */
export function renderSettingsGrid({ prefix, playerCount, gameType = 'kachuful' }) {
  if (gameType === 'scoresheet') {
    return `
    <div class="settings-grid" data-game-settings="scoresheet">
      <label for="${prefix}-label">Label</label>
      <input type="text" id="${prefix}-label" maxlength="80" placeholder="e.g. Declare" aria-label="Scoresheet label" />

      <label for="${prefix}-winner">Winner</label>
      <select id="${prefix}-winner" aria-label="Winner">
        <option value="highest" selected>Highest total</option>
        <option value="lowest">Lowest total</option>
      </select>

      <label>Show totals</label>
      <label class="toggle">
        <input type="checkbox" id="${prefix}-show-totals" checked>
        <span class="toggle-label">On</span>
      </label>

      <label>Allow negatives</label>
      <label class="toggle">
        <input type="checkbox" id="${prefix}-allow-negatives">
        <span class="toggle-label">Off</span>
      </label>

      <label>Appearance</label>
      <select id="${prefix}-appearance">
        <option value="interactive" selected>Navy (off-white)</option>
        <option value="standard">Standard</option>
      </select>
    </div>
  `;
  }

  const maxCards = maxCardsForPlayers(playerCount);
  const defaultCards = Math.min(maxCards, 8);

  return `
    <div class="settings-grid" data-game-settings="kachuful">
      <label>Mode</label>
      <select id="${prefix}-mode">
        <option value="expert">Expert</option>
        <option value="rookie" selected>Rookie</option>
        <option value="friendly">Friendly</option>
      </select>

      <label>Appearance</label>
      <select id="${prefix}-appearance">
        <option value="standard">Standard</option>
        <option value="interactive" selected>Interactive</option>
      </select>

      <label>Cards per round</label>
      <select id="${prefix}-cards">
        ${renderCardsOptions(maxCards, defaultCards)}
      </select>

      <label>Scoring</label>
      <select id="${prefix}-scoring">
        <option value="kachuful_standard" selected>Ones (bid 1 = 11)</option>
        <option value="kachuful_zeros">Zeros (bid 1 = 10)</option>
      </select>

      <label>Sets</label>
      <select id="${prefix}-sets">
        ${[1, 2, 3, 4, 5].map(n =>
          `<option value="${n}" ${n === 3 ? 'selected' : ''}>${n} set${n > 1 ? 's' : ''}</option>`
        ).join('')}
      </select>

      <label>Must-lose</label>
      <label class="toggle">
        <input type="checkbox" id="${prefix}-must-lose" checked>
        <span class="toggle-label">On</span>
      </label>
    </div>
  `;
}

/**
 * Read current settings values from the rendered grid.
 *
 * @param {HTMLElement} container — parent element containing the settings grid
 * @param {string} prefix — ID prefix used in renderSettingsGrid
 * @param {string} [gameType] — when scoresheet, read Scoresheet fields
 * @returns {Object} Settings object ready for createGame
 */
export function readSettings(container, prefix, gameType) {
  const resolvedType =
    gameType ||
    container.querySelector('[data-game-settings]')?.getAttribute('data-game-settings') ||
    'kachuful';

  if (resolvedType === 'scoresheet') {
    const showTotals = container.querySelector(`#${prefix}-show-totals`);
    const allowNegatives = container.querySelector(`#${prefix}-allow-negatives`);
    return {
      game_type: 'scoresheet',
      label: (container.querySelector(`#${prefix}-label`)?.value || '').trim(),
      winner: container.querySelector(`#${prefix}-winner`)?.value || 'highest',
      show_totals: showTotals ? showTotals.checked : true,
      allow_negatives: allowNegatives ? allowNegatives.checked : false,
      appearance: container.querySelector(`#${prefix}-appearance`)?.value || 'interactive',
    };
  }

  return {
    mode: container.querySelector(`#${prefix}-mode`).value,
    appearance: container.querySelector(`#${prefix}-appearance`).value,
    scoring_formula: container.querySelector(`#${prefix}-scoring`).value,
    num_sets: parseInt(container.querySelector(`#${prefix}-sets`).value),
    rounds_per_set: parseInt(container.querySelector(`#${prefix}-cards`).value),
    must_lose: container.querySelector(`#${prefix}-must-lose`).checked,
  };
}

/**
 * Update the cards dropdown when player count changes.
 *
 * @param {HTMLElement} container
 * @param {string} prefix
 * @param {number} playerCount
 */
export function updateCardsDropdown(container, prefix, playerCount) {
  const maxCards = maxCardsForPlayers(playerCount);
  const select = container.querySelector(`#${prefix}-cards`);
  const currentValue = parseInt(select.value);
  const clampedValue = Math.min(currentValue, maxCards);
  select.innerHTML = renderCardsOptions(maxCards, clampedValue);
}

/**
 * Keep On/Off toggle labels in sync with checkbox state.
 * @param {HTMLElement} container
 */
export function bindToggleLabels(container) {
  if (!container) return;
  container.querySelectorAll('label.toggle input[type="checkbox"]').forEach((checkbox) => {
    const label = checkbox.parentElement?.querySelector('.toggle-label');
    if (!label) return;
    const sync = () => {
      label.textContent = checkbox.checked ? 'On' : 'Off';
    };
    sync();
    checkbox.addEventListener('change', sync);
  });
}

