// Lobby screen — player setup, settings, start game

import { getPlayground, createGame as createServerGame, getActiveGame as getServerActiveGame } from '../api.js';
import { createOnlineGame, loadGameFromServer, endGame as endLocalGame, confirmFinal as confirmLocalFinal } from '../game-api.js';
import { initDragReorder } from '../components/drag-reorder.js';
import { escapeHtml } from '../components/game-utils.js';
import { renderSettingsGrid, readSettings } from '../components/game-settings.js';
import { isMuted, toggleMute, soundEndGame } from '../components/sounds.js';
import { showConfirmDialog } from '../components/confirm-dialog.js';
import { getSyncPendingGames, attemptSyncBack } from '../engine/sync-manager.js';
import { getActiveGameForRoom } from '../engine/store.js';

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

        // Prefer local IDB active game for this room (IDB-first local game- ids).
        let activeGame = await getActiveGameForRoom(playground.share_code);
        if (!activeGame) {
            try {
                const serverActive = await getServerActiveGame(playground.id);
                if (serverActive) {
                    activeGame = await loadGameFromServer(serverActive.id);
                }
            } catch { /* no active game */ }
        }

        function renderLobby() {
            container.innerHTML = `
                <div class="lobby">
                    <div class="lobby-header">
                        <button class="btn-text" id="lobby-home" style="position:absolute;left:16px;">← Home</button>
                        <h2>${escapeHtml(playground.name)}</h2>
                        <p class="share-code">Code: <strong>${escapeHtml(playground.share_code)}</strong></p>
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

                    <div id="sync-section" class="hidden" style="margin-bottom:12px;">
                        <button id="sync-now" class="btn btn-primary btn-small">Sync now</button>
                        <p id="sync-result" class="hidden" role="status" aria-live="polite" style="margin-top:6px;font-size:0.85rem;"></p>
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
                        <button id="toggle-sound" class="btn btn-large" style="flex:0;" aria-label="${isMuted() ? 'Unmute sound' : 'Mute sound'}">${isMuted() ? '🔇' : '🔊'}</button>
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

            // End active game from lobby — must finish on server (/end + /confirm-final)
            // or Resume stays forever (active endpoint keys off status=active).
            const endActiveBtn = container.querySelector('#end-active-game');
            if (endActiveBtn) {
                endActiveBtn.addEventListener('click', async () => {
                    const confirmed = await showConfirmDialog('End this game? Scores so far will be saved.');
                    if (confirmed) {
                        const gameId = activeGame.id;
                        try { await endLocalGame(gameId); } catch { /* may already be finished */ }
                        try { await confirmLocalFinal(gameId); } catch { /* server finalize retried on online */ }
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
                    const serverGame = await createServerGame(playground.id, players, settings);
                    const game = await createOnlineGame(
                        serverGame.id,
                        players,
                        settings,
                        playground.share_code,
                    );
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
                const soundBtn = container.querySelector('#toggle-sound');
                soundBtn.textContent = muted ? '🔇' : '🔊';
                soundBtn.setAttribute('aria-label', muted ? 'Unmute sound' : 'Mute sound');
            });

            // Sync button — uses SyncManager.syncPending (correct 4xx = failed)
            const syncBtn = container.querySelector('#sync-now');
            if (syncBtn) {
                syncBtn.addEventListener('click', async () => {
                    const resultEl = container.querySelector('#sync-result');
                    syncBtn.disabled = true;
                    resultEl.classList.remove('hidden');
                    resultEl.textContent = 'Syncing...';

                    const result = await attemptSyncBack(shareCode);
                    const synced = result.synced ?? 0;
                    const failed = result.failed ?? 0;

                    if (result.skipped && synced === 0 && failed === 0) {
                        resultEl.textContent = 'Could not reach server. Retry?';
                        syncBtn.disabled = false;
                        return;
                    }

                    if (failed === 0) {
                        resultEl.textContent = synced === 0
                            ? 'Nothing to sync'
                            : `${synced} game${synced === 1 ? '' : 's'} synced!`;
                        syncTimer = setTimeout(() => {
                            container.querySelector('#sync-section')?.classList.add('hidden');
                        }, 3000);
                    } else {
                        resultEl.textContent = `${synced} synced, ${failed} failed. Retry?`;
                        syncBtn.disabled = false;
                    }
                });
            }
        }

        async function checkPendingSyncs() {
            try {
                const pendingGames = await getSyncPendingGames(shareCode);
                const syncSection = container.querySelector('#sync-section');
                if (syncSection) {
                    if (pendingGames.length > 0) {
                        syncSection.classList.remove('hidden');
                    } else {
                        syncSection.classList.add('hidden');
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
