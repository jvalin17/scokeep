// Lobby screen — player setup, settings, start game

import { getPlayground, createGame, getActiveGame, endGame } from '../api.js';
import { initDragReorder } from '../components/drag-reorder.js';
import { isMuted, toggleMute, soundEndGame } from '../components/sounds.js';

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
        } catch (e) { console.warn('No active game:', e.message); }

        function renderLobby() {
            container.innerHTML = `
                <div class="lobby">
                    <div class="lobby-header">
                        <button class="btn-text" onclick="location.hash=''" style="position:absolute;left:16px;">← Home</button>
                        <h2>${playground.name}</h2>
                        <p class="share-code">Code: <strong>${playground.share_code}</strong></p>
                    </div>

                    ${activeGame ? `
                        <div class="active-game-actions">
                            <button id="resume-game" class="btn btn-primary btn-large">Resume Game (Round ${activeGame.current_round})</button>
                            <button id="end-active-game" class="btn btn-large" style="background:var(--danger);color:#fff;">End Game</button>
                        </div>
                    ` : ''}

                    <section class="lobby-section">
                        <h3>Players</h3>
                        <div id="player-list" class="lobby-player-list">
                            ${players.map((name, index) => `
                                <div class="lobby-player" data-index="${index}">
                                    <span class="drag-handle" data-drag="${index}">&#9776;</span>
                                    <span class="player-name-display">${name}</span>
                                    <button class="btn-remove" data-remove="${index}">&times;</button>
                                </div>
                            `).join('')}
                        </div>
                        <div class="add-player-row">
                            <input type="text" id="new-player" placeholder="Add player"
                                maxlength="15" autocomplete="off">
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

                            <label>Set type</label>
                            <select id="setting-set-type">
                                <option value="8" selected>Standard (8 cards)</option>
                                <option value="4">Test (4 cards)</option>
                            </select>

                            <label>Sets</label>
                            <select id="setting-sets">
                                ${[1,2,3,4,5].map(n =>
                                    `<option value="${n}" ${n === 3 ? 'selected' : ''}>${n} set${n > 1 ? 's' : ''}</option>`
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
                    <div style="display:flex;gap:8px;margin-top:8px;">
                        <button id="view-stats" class="btn btn-large" style="flex:1;">📊 Stats</button>
                        <button id="toggle-sound" class="btn btn-large" style="flex:0;">${isMuted() ? '🔇' : '🔊'}</button>
                    </div>
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
                    const phase = activeGame.phase;
                    if (phase === 'bidding') { navigate(`bid/${activeGame.id}`); return; }
                    if (phase === 'playing') { navigate(`play/${activeGame.id}`); return; }
                    if (phase === 'round_end') { navigate(`roundend/${activeGame.id}`); return; }
                    if (phase === 'final') { navigate(`final/${activeGame.id}`); return; }
                    navigate(`scoreboard/${activeGame.id}`);
                });
            }

            // End active game from lobby
            const endActiveBtn = container.querySelector('#end-active-game');
            if (endActiveBtn) {
                endActiveBtn.addEventListener('click', async () => {
                    if (confirm('End this game? Scores so far will be saved.')) {
                        const gameId = activeGame.id;
                        await endGame(gameId);
                        soundEndGame();
                        navigate(`scoreboard/${gameId}`);
                    }
                });
            }

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
            initDragReorder(container, playerList, players, renderLobby);

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

                const numSets = parseInt(container.querySelector('#setting-sets').value);
                const roundsPerSet = parseInt(container.querySelector('#setting-set-type').value);
                const settings = {
                    game_type: 'kachuful',
                    mode: container.querySelector('#setting-mode').value,
                    appearance: container.querySelector('#setting-appearance').value,
                    num_sets: numSets,
                    rounds_per_set: roundsPerSet,
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

            container.querySelector('#view-stats').addEventListener('click', () => {
                navigate(`stats/${playground.share_code}`);
            });

            container.querySelector('#toggle-sound').addEventListener('click', () => {
                const muted = toggleMute();
                container.querySelector('#toggle-sound').textContent = muted ? '🔇' : '🔊';
            });

        }

        renderLobby();
    },

    unmount() {},
};
