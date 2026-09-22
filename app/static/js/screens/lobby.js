// Lobby screen — player setup, settings, start game

import { getPlayground, createGame, getActiveGame, endGame } from '../api.js';
import { initDragReorder } from '../components/drag-reorder.js';
import { escapeHtml } from '../components/game-utils.js';
import { renderSettingsGrid, readSettings } from '../components/game-settings.js';
import { isMuted, toggleMute, soundEndGame } from '../components/sounds.js';
import { showConfirmDialog } from '../components/confirm-dialog.js';
import { getSyncPendingGames, syncOneGame } from '../engine/sync-import.js';

let syncTimer = null;

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
                        <button class="btn-text" id="lobby-home" style="position:absolute;left:16px;">← Home</button>
                        <h2>${escapeHtml(playground.name)}</h2>
                        <p class="share-code">Code: <strong>${playground.share_code}</strong></p>
                    </div>

                    ${activeGame ? `
                        <div class="active-game-actions">
                            <button id="resume-game" class="btn btn-primary btn-large">Resume Game (Round ${activeGame.current_round})</button>
                            <button id="game-settings-toggle" class="btn-text" style="font-size:0.8rem;margin-top:8px;">⚙ Options</button>
                            <div id="game-settings-panel" class="hidden" style="margin-top:8px;">
                                <button id="end-active-game" class="btn-small" style="background:var(--danger);color:#fff;font-size:0.8rem;">End Game</button>
                            </div>
                        </div>
                    ` : ''}

                    <div id="sync-banner" class="hidden" style="background:var(--bg-card);border:1px solid var(--accent);border-radius:8px;padding:12px;margin-bottom:12px;">
                        <p id="sync-message" style="margin:0 0 8px;font-size:0.9rem;"></p>
                        <button id="sync-now" class="btn btn-primary btn-small">Sync now</button>
                    </div>

                    <section class="lobby-section">
                        <h3>Players</h3>
                        <div id="player-list" class="lobby-player-list">
                            ${players.map((name, index) => `
                                <div class="lobby-player" data-index="${index}">
                                    <span class="drag-handle" data-drag="${index}">&#9776;</span>
                                    <span class="player-name-display">${escapeHtml(name)}</span>
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
                        ${renderSettingsGrid({ prefix: 'setting', playerCount: players.length })}

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
            checkPendingSyncs();
        }

        function bindEvents() {
            // Home button
            const homeBtn = container.querySelector('#lobby-home');
            if (homeBtn) homeBtn.addEventListener('click', () => { location.hash = ''; });

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

            // Game settings toggle
            const settingsToggle = container.querySelector('#game-settings-toggle');
            if (settingsToggle) {
                settingsToggle.addEventListener('click', () => {
                    container.querySelector('#game-settings-panel').classList.toggle('hidden');
                });
            }

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
                    const confirmed = await showConfirmDialog('End this game? Scores so far will be saved.');
                    if (confirmed) {
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
            if (lobbyScreen._cleanupDrag) lobbyScreen._cleanupDrag();
            lobbyScreen._cleanupDrag = initDragReorder(container, playerList, players, renderLobby);

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
                    game_type: 'kachuful',
                    ...readSettings(container, 'setting'),
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

            // Sync banner — sync pending offline games
            const syncBtn = container.querySelector('#sync-now');
            if (syncBtn) {
                syncBtn.addEventListener('click', async () => {
                    const messageEl = container.querySelector('#sync-message');
                    syncBtn.disabled = true;

                    const pendingGames = await getSyncPendingGames(shareCode);
                    const total = pendingGames.length;
                    let synced = 0;
                    let failed = 0;

                    for (const game of pendingGames) {
                        messageEl.textContent = `Syncing ${synced + 1} of ${total}...`;
                        const result = await syncOneGame(game);
                        if (result.success) { synced++; }
                        else { failed++; }
                    }

                    if (failed === 0) {
                        messageEl.textContent = `All ${synced} game${synced > 1 ? 's' : ''} synced!`;
                        syncTimer = setTimeout(() => {
                            container.querySelector('#sync-banner')?.classList.add('hidden');
                        }, 2000);
                    } else {
                        messageEl.textContent = `${synced} synced, ${failed} failed. Retry later.`;
                        syncBtn.disabled = false;
                    }
                });
            }
        }

        async function checkPendingSyncs() {
            try {
                const pendingGames = await getSyncPendingGames(shareCode);
                if (pendingGames.length > 0) {
                    const banner = container.querySelector('#sync-banner');
                    const messageEl = container.querySelector('#sync-message');
                    if (banner && messageEl) {
                        const count = pendingGames.length;
                        messageEl.textContent = `You have ${count} unsynced offline game${count > 1 ? 's' : ''}. Sync now?`;
                        banner.classList.remove('hidden');
                    }
                }
            } catch (error) {
                console.warn('Failed to check pending syncs:', error);
            }
        }

        renderLobby();
    },

    unmount() {
        clearTimeout(syncTimer);
        syncTimer = null;
        if (lobbyScreen._cleanupDrag) {
            lobbyScreen._cleanupDrag();
            lobbyScreen._cleanupDrag = null;
        }
    },
};
