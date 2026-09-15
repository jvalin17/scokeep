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
 * Render the full settings grid HTML.
 *
 * @param {Object} options
 * @param {string} options.prefix — ID prefix (e.g. 'setting', 'quick-setting')
 * @param {number} options.playerCount — number of players (for max cards calculation)
 * @returns {string} HTML string
 */
export function renderSettingsGrid({ prefix, playerCount }) {
  const maxCards = maxCardsForPlayers(playerCount);
  const defaultCards = Math.min(maxCards, 8);

  return `
    <div class="settings-grid">
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
 * @returns {Object} Settings object ready for createGame
 */
export function readSettings(container, prefix) {
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
