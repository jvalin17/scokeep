// Lobby screen — player setup, settings, start game

import { getPlayground, createGame } from '../api.js';

export const lobbyScreen = {
    async mount(container, state, { navigate, params }) {
        const shareCode = params[0];
        if (!state.playground) {
            try {
                state.playground = await getPlayground(shareCode);
            } catch {
                navigate('');
                return;
            }
        }

        const playground = state.playground;
        let players = [...playground.players];

        function renderLobby() {
            container.innerHTML = `
                <div class="lobby">
                    <div class="lobby-header">
                        <h2>${playground.name}</h2>
                        <p class="share-code">Code: <strong>${playground.share_code}</strong></p>
                    </div>

                    <section class="lobby-section">
                        <h3>Players</h3>
                        <div id="player-list" class="lobby-player-list">
                            ${players.map((name, index) => `
                                <div class="lobby-player" data-index="${index}">
                                    <span class="drag-handle" data-drag="${index}">&#9776;</span>
                                    <span class="player-name-display">${name}</span>
                                    ${players.length > 2 ? `<button class="btn-remove" data-remove="${index}">&times;</button>` : ''}
                                </div>
                            `).join('')}
                        </div>
                        <div class="add-player-row">
                            <input type="text" id="new-player" placeholder="Add player"
                                maxlength="20" autocomplete="off">
                            <button id="add-player-btn" class="btn-small">Add</button>
                        </div>
                    </section>

                    <section class="lobby-section">
                        <h3>Settings</h3>
                        <div class="settings-grid">
                            <label>Mode</label>
                            <select id="setting-mode">
                                <option value="expert">Expert</option>
                                <option value="rookie" selected>Rookie</option>
                                <option value="friendly">Friendly</option>
                            </select>

                            <label>Appearance</label>
                            <select id="setting-appearance">
                                <option value="standard">Standard</option>
                                <option value="interactive" selected>Interactive</option>
                            </select>

                            <label>Review timer</label>
                            <select id="setting-timer">
                                <option value="3" selected>3 seconds</option>
                                <option value="5">5 seconds</option>
                                <option value="10">10 seconds</option>
                                <option value="15">15 seconds</option>
                            </select>

                            <label>Sets</label>
                            <select id="setting-sets">
                                ${[1,2,3,4,5].map(n =>
                                    `<option value="${n}" ${n === 3 ? 'selected' : ''}>${n} set${n > 1 ? 's' : ''} (${n * 8} rounds)</option>`
                                ).join('')}
                            </select>

                            <label>Must-lose</label>
                            <label class="toggle">
                                <input type="checkbox" id="setting-must-lose" checked>
                                <span class="toggle-label">On</span>
                            </label>
                        </div>
                    </section>

                    <button id="start-game" class="btn btn-primary btn-large">Start Game</button>
                    <p id="lobby-error" class="error hidden"></p>
                </div>
            `;

            bindEvents();
        }

        function bindEvents() {
            // Add player
            const addBtn = container.querySelector('#add-player-btn');
            const newPlayerInput = container.querySelector('#new-player');
            addBtn.addEventListener('click', () => {
                const name = newPlayerInput.value.trim();
                if (name && players.length < 8) {
                    players.push(name);
                    renderLobby();
                }
            });
            newPlayerInput.addEventListener('keydown', (event) => {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    addBtn.click();
                }
            });

            // Remove player
            container.querySelectorAll('[data-remove]').forEach(btn => {
                btn.addEventListener('click', () => {
                    const index = parseInt(btn.dataset.remove);
                    players.splice(index, 1);
                    renderLobby();
                });
            });

            // Touch drag to reorder
            const playerList = container.querySelector('#player-list');
            let dragEl = null;
            let dragIndex = null;
            let startY = 0;
            let currentY = 0;

            container.querySelectorAll('.drag-handle').forEach(handle => {
                handle.addEventListener('touchstart', (e) => {
                    e.preventDefault();
                    dragIndex = parseInt(handle.dataset.drag);
                    dragEl = handle.closest('.lobby-player');
                    startY = e.touches[0].clientY;
                    currentY = startY;
                    dragEl.classList.add('dragging');
                }, { passive: false });
            });

            document.addEventListener('touchmove', (e) => {
                if (dragEl === null) return;
                e.preventDefault();
                currentY = e.touches[0].clientY;
                dragEl.style.transform = `translateY(${currentY - startY}px)`;

                // Find which player we're over
                const items = [...playerList.querySelectorAll('.lobby-player')];
                for (const item of items) {
                    if (item === dragEl) continue;
                    const rect = item.getBoundingClientRect();
                    const mid = rect.top + rect.height / 2;
                    if (currentY < mid && parseInt(item.dataset.index) < dragIndex) {
                        item.style.transform = 'translateY(48px)';
                    } else if (currentY > mid && parseInt(item.dataset.index) > dragIndex) {
                        item.style.transform = 'translateY(-48px)';
                    } else {
                        item.style.transform = '';
                    }
                }
            }, { passive: false });

            document.addEventListener('touchend', () => {
                if (dragEl === null) return;
                // Find drop target
                const items = [...playerList.querySelectorAll('.lobby-player')];
                let dropIndex = dragIndex;
                for (const item of items) {
                    if (item === dragEl) continue;
                    const rect = item.getBoundingClientRect();
                    const mid = rect.top + rect.height / 2;
                    const idx = parseInt(item.dataset.index);
                    if (currentY < mid && idx < dragIndex) {
                        dropIndex = Math.min(dropIndex, idx);
                    } else if (currentY > mid && idx > dragIndex) {
                        dropIndex = Math.max(dropIndex, idx);
                    }
                }
                if (dropIndex !== dragIndex) {
                    const moved = players.splice(dragIndex, 1)[0];
                    players.splice(dropIndex, 0, moved);
                }
                dragEl = null;
                dragIndex = null;
                renderLobby();
            });

            // Must-lose toggle label
            const mustLoseCheckbox = container.querySelector('#setting-must-lose');
            mustLoseCheckbox.addEventListener('change', () => {
                mustLoseCheckbox.nextElementSibling.textContent =
                    mustLoseCheckbox.checked ? 'On' : 'Off';
            });

            // Start game
            container.querySelector('#start-game').addEventListener('click', async () => {
                const errorElement = container.querySelector('#lobby-error');
                errorElement.classList.add('hidden');

                const settings = {
                    mode: container.querySelector('#setting-mode').value,
                    appearance: container.querySelector('#setting-appearance').value,
                    timer_seconds: parseInt(container.querySelector('#setting-timer').value),
                    num_sets: parseInt(container.querySelector('#setting-sets').value),
                    must_lose: container.querySelector('#setting-must-lose').checked,
                };

                try {
                    const game = await createGame(playground.id, players, settings);
                    state.game = game;
                    document.body.setAttribute('data-appearance', settings.appearance);
                    navigate(`bid/${game.id}`);
                } catch (error) {
                    errorElement.textContent = error.message;
                    errorElement.classList.remove('hidden');
                }
            });
        }

        renderLobby();
    },

    unmount() {},
};
