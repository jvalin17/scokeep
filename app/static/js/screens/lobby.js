// Lobby screen — player setup, settings, start game

import { getPlayground, createGame, getActiveGame } from '../api.js';

export const lobbyScreen = {
    async mount(container, state, { navigate, params }) {
        document.body.setAttribute('data-phase', 'home');
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

        // Check for active game
        let activeGame = null;
        try {
            activeGame = await getActiveGame(playground.id);
        } catch { /* no active game */ }

        function renderLobby() {
            container.innerHTML = `
                <div class="lobby">
                    <div class="lobby-header">
                        <button class="btn-text" onclick="location.hash=''" style="position:absolute;left:16px;">← Home</button>
                        <h2>${playground.name}</h2>
                        <p class="share-code">Code: <strong>${playground.share_code}</strong></p>
                    </div>

                    ${activeGame ? `
                        <button id="resume-game" class="btn btn-primary btn-large">Resume Game (Round ${activeGame.current_round})</button>
                    ` : ''}

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
                        <h3>Game Type</h3>
                        <div class="game-type-tabs">
                            <button class="game-type-tab active" data-type="kachuful">Kachuful</button>
                            <button class="game-type-tab" data-type="free">Free Score</button>
                        </div>

                        <div id="kachuful-settings" class="settings-grid">
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

                        <div id="free-settings" class="settings-grid" style="display: none;">
                            <label>Rounds</label>
                            <input type="number" id="setting-free-rounds" value="10" min="1" max="99"
                                style="width: 80px; text-align: center;">

                            <label>Appearance</label>
                            <select id="setting-free-appearance">
                                <option value="standard">Standard</option>
                                <option value="interactive" selected>Interactive</option>
                            </select>
                        </div>
                    </section>

                    <button id="start-game" class="btn btn-primary btn-large">Start Game</button>
                    <button id="view-stats" class="btn btn-large" style="margin-top: 8px;">📊 Stats</button>
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

            // Resume active game
            const resumeBtn = container.querySelector('#resume-game');
            if (resumeBtn) {
                resumeBtn.addEventListener('click', () => {
                    state.game = activeGame;
                    document.body.setAttribute('data-appearance', activeGame.settings.appearance || 'standard');
                    if (activeGame.settings.game_type === 'free') {
                        navigate(`freescore/${activeGame.id}`);
                        return;
                    }
                    const phase = activeGame.phase;
                    if (phase === 'bidding') { navigate(`bid/${activeGame.id}`); return; }
                    if (phase === 'playing') { navigate(`play/${activeGame.id}`); return; }
                    if (phase === 'round_end') { navigate(`roundend/${activeGame.id}`); return; }
                    if (phase === 'final') { navigate(`final/${activeGame.id}`); return; }
                    navigate(`scoreboard/${activeGame.id}`);
                });
            }

            // Game type tabs
            let gameType = 'kachuful';
            container.querySelectorAll('.game-type-tab').forEach(tab => {
                tab.addEventListener('click', () => {
                    gameType = tab.dataset.type;
                    container.querySelectorAll('.game-type-tab').forEach(t => t.classList.remove('active'));
                    tab.classList.add('active');
                    container.querySelector('#kachuful-settings').style.display = gameType === 'kachuful' ? '' : 'none';
                    container.querySelector('#free-settings').style.display = gameType === 'free' ? '' : 'none';
                });
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

                let settings;
                if (gameType === 'kachuful') {
                    settings = {
                        game_type: 'kachuful',
                        mode: container.querySelector('#setting-mode').value,
                        appearance: container.querySelector('#setting-appearance').value,
                        num_sets: parseInt(container.querySelector('#setting-sets').value),
                        must_lose: container.querySelector('#setting-must-lose').checked,
                    };
                } else {
                    settings = {
                        game_type: 'free',
                        mode: 'friendly',
                        scoring_formula: 'free_raw',
                        appearance: container.querySelector('#setting-free-appearance').value,
                        num_sets: 1,
                        must_lose: false,
                        free_rounds: parseInt(container.querySelector('#setting-free-rounds').value) || 10,
                    };
                }

                try {
                    const game = await createGame(playground.id, players, settings);
                    state.game = game;
                    document.body.setAttribute('data-appearance', settings.appearance);
                    if (gameType === 'free') {
                        navigate(`freescore/${game.id}`);
                    } else {
                        navigate(`bid/${game.id}`);
                    }
                } catch (error) {
                    errorElement.textContent = error.message;
                    errorElement.classList.remove('hidden');
                }
            });

            container.querySelector('#view-stats').addEventListener('click', () => {
                navigate(`stats/${playground.share_code}`);
            });

        }

        renderLobby();
    },

    unmount() {},
};
