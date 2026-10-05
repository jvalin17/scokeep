// Lobby screen — player setup, settings, start game

import { getPlayground, createGame as createServerGame, getActiveGame as getServerActiveGame } from '../api.js';
import { createOnlineGame, loadGameFromServer, endGame as endLocalGame, confirmFinal as confirmLocalFinal } from '../game-api.js';
import { initDragReorder } from '../components/drag-reorder.js';
import { escapeHtml } from '../components/game-utils.js';
import { renderSettingsGrid, renderGameTypeTabs, readSettings, bindToggleLabels } from '../components/game-settings.js';
import { isMuted, toggleMute, soundEndGame } from '../components/sounds.js';
import { showConfirmDialog } from '../components/confirm-dialog.js';
import { getSyncPendingGames, attemptSyncBack, retrySyncQueue } from '../engine/sync-manager.js';
import { getActiveGameForRoom, getSyncQueue } from '../engine/store.js';
import { logger } from '../components/logger.js';
import { getPack, startRouteFor, routeFor } from '../packs/registry.js';
import { initialGameTypeForLobby, renderResumeBlock } from './lobby-resume.js';

let syncTimer = null;

export const lobbyScreen = {
    async mount(container, state, { navigate, params }) {
        document.body.setAttribute('data-phase', 'home');
        const shareCode = params[0];
        if (!state.playground) {
            try {
                state.playground = await getPlayground(shareCode);
            } catch (error) {
                logger.warn('lobby', `Failed to load playground: ${error?.message || error}`);
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
            } catch (error) {
                logger.warn('lobby', `No server active game: ${error?.message || error}`);
            }
        }
        let selectedGameType = initialGameTypeForLobby(activeGame);

        function renderLobby() {
            container.innerHTML = `
                <div class="lobby">
                    <div class="lobby-header">
                        <button class="btn-text" id="lobby-home" style="position:absolute;left:16px;">← Home</button>
                        <h2>${escapeHtml(playground.name)}</h2>
                        <p class="share-code">Code: <strong>${escapeHtml(playground.share_code)}</strong></p>
                    </div>

                    ${renderResumeBlock(activeGame, selectedGameType)}

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
                                    <button class="btn-remove" data-remove="${index}" aria-label="Remove ${escapeHtml(name)}">&times;</button>
                                </div>
                            `).join('')}
                        </div>
                        <div class="add-player-row">
                            <input type="text" id="new-player" placeholder="Add player"
                                maxlength="15" autocomplete="off">
                            <button type="button" id="add-player-btn" class="btn-small">Add</button>
                        </div>
                    </section>

                    <section class="lobby-section">
                        <h3>Game</h3>
                        ${renderGameTypeTabs(selectedGameType)}
                        <div id="lobby-settings-host" class="lobby-game-settings" role="tabpanel"
                            aria-labelledby="${selectedGameType === 'scoresheet' ? 'game-tab-scoresheet' : 'game-tab-kachuful'}">
                        ${renderSettingsGrid({
                            prefix: 'setting',
                            playerCount: players.length,
                            gameType: selectedGameType,
                        })}
                        </div>
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


        function showLobbyError(message) {
            const errorEl = container.querySelector('#lobby-error');
            if (!errorEl) return;
            errorEl.textContent = message;
            errorEl.classList.remove('hidden');
        }

        function bindHomeAndPlayers() {
            const homeBtn = container.querySelector('#lobby-home');
            if (homeBtn) homeBtn.addEventListener('click', () => { location.hash = ''; });

            const addBtn = container.querySelector('#add-player-btn');
            const newPlayerInput = container.querySelector('#new-player');
            addBtn.addEventListener('click', () => {
                const name = newPlayerInput.value.trim();
                if (!name) {
                    showLobbyError('Enter a player name first');
                    newPlayerInput.focus();
                    return;
                }
                if (players.length >= 8) {
                    showLobbyError('Maximum 8 players');
                    return;
                }
                container.querySelector('#lobby-error')?.classList.add('hidden');
                players.push(name);
                renderLobby();
            });
            newPlayerInput.addEventListener('keydown', (event) => {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    addBtn.click();
                }
            });

            container.querySelectorAll('[data-remove]').forEach(btn => {
                btn.addEventListener('click', () => {
                    const index = parseInt(btn.dataset.remove);
                    players.splice(index, 1);
                    renderLobby();
                });
            });

            const playerList = container.querySelector('#player-list');
            if (lobbyScreen._cleanupDrag) lobbyScreen._cleanupDrag();
            lobbyScreen._cleanupDrag = initDragReorder(container, playerList, players, renderLobby);
        }

        function bindResumeAndEnd() {
            const settingsToggle = container.querySelector('#game-settings-toggle');
            if (settingsToggle) {
                settingsToggle.addEventListener('click', () => {
                    container.querySelector('#game-settings-panel').classList.toggle('hidden');
                });
            }

            const resumeBtn = container.querySelector('#resume-game');
            if (resumeBtn) {
                resumeBtn.addEventListener('click', () => {
                    state.game = activeGame;
                    document.body.setAttribute('data-appearance', activeGame.settings.appearance || 'standard');
                    const screen = routeFor(activeGame);
                    navigate(`${screen}/${activeGame.id}`);
                });
            }

            const endActiveBtn = container.querySelector('#end-active-game');
            if (!endActiveBtn) return;
            endActiveBtn.addEventListener('click', async () => {
                const confirmed = await showConfirmDialog('End this game? Scores so far will be saved.');
                if (!confirmed) return;
                const gameId = activeGame.id;
                const errorEl = container.querySelector('#lobby-error');
                endActiveBtn.disabled = true;
                try {
                    try { await endLocalGame(gameId); } catch { /* may already be finished */ }
                    const finished = await confirmLocalFinal(gameId);
                    if (finished.server_end_pending || finished.sync_pending) {
                        if (errorEl) {
                            errorEl.textContent = 'Could not finish on server — check connection and tap Sync now, then End Game again.';
                            errorEl.classList.remove('hidden');
                        }
                        const syncSection = container.querySelector('#sync-section');
                        if (syncSection) syncSection.classList.remove('hidden');
                        return;
                    }
                    soundEndGame();
                    navigate(`scoreboard/${gameId}`);
                } catch {
                    if (errorEl) {
                        errorEl.textContent = 'Could not end game — try again when online.';
                        errorEl.classList.remove('hidden');
                    }
                } finally {
                    endActiveBtn.disabled = false;
                }
            });
        }

        function bindGameTypeTabs() {
            container.querySelectorAll('[data-game-tab]').forEach((tab) => {
                tab.addEventListener('click', () => {
                    const nextType = tab.getAttribute('data-game-tab') || 'kachuful';
                    if (nextType === selectedGameType) return;
                    selectedGameType = nextType;
                    renderLobby();
                });
            });
            bindToggleLabels(container);
            const mustLoseCheckbox = container.querySelector('#setting-must-lose');
            if (mustLoseCheckbox) {
                mustLoseCheckbox.addEventListener('change', () => {
                    mustLoseCheckbox.nextElementSibling.textContent =
                        mustLoseCheckbox.checked ? 'On' : 'Off';
                });
            }
        }

        function bindStartAndChrome() {
            container.querySelector('#start-game').addEventListener('click', async () => {
                const errorElement = container.querySelector('#lobby-error');
                errorElement.classList.add('hidden');

                const gameType = selectedGameType || 'kachuful';
                const pack = getPack(gameType);
                const settings = {
                    ...pack.settingsDefaults,
                    ...readSettings(container, 'setting', gameType),
                    game_type: gameType,
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
                    document.body.setAttribute('data-appearance', settings.appearance || 'standard');
                    document.body.setAttribute('data-game-type', gameType || 'kachuful');
                    const startScreen = startRouteFor(gameType);
                    navigate(`${startScreen}/${game.id}`);
                } catch (error) {
                    errorElement.textContent = error.message;
                    errorElement.classList.remove('hidden');
                }
            });

            container.querySelector('#view-stats').addEventListener('click', () => {
                navigate(`stats/${playground.share_code}/${selectedGameType || 'kachuful'}`);
            });

            container.querySelector('#toggle-sound').addEventListener('click', () => {
                const muted = toggleMute();
                const soundBtn = container.querySelector('#toggle-sound');
                soundBtn.textContent = muted ? '🔇' : '🔊';
                soundBtn.setAttribute('aria-label', muted ? 'Unmute sound' : 'Mute sound');
            });

            const syncBtn = container.querySelector('#sync-now');
            if (!syncBtn) return;
            syncBtn.addEventListener('click', async () => {
                const resultEl = container.querySelector('#sync-result');
                syncBtn.disabled = true;
                syncBtn.setAttribute('aria-busy', 'true');
                resultEl.classList.remove('hidden');
                resultEl.textContent = 'Syncing...';

                const queueResult = await retrySyncQueue();
                const result = await attemptSyncBack(shareCode);
                const synced = result.synced ?? 0;
                const failed = result.failed ?? 0;
                const queueFailed = queueResult.failed || !queueResult.drained;

                if (result.skipped && synced === 0 && failed === 0 && queueResult.drained) {
                    resultEl.textContent = 'Could not reach server. Retry?';
                    syncBtn.disabled = false;
                    syncBtn.removeAttribute('aria-busy');
                    return;
                }

                if (failed === 0 && !queueFailed) {
                    const queueSynced = queueResult.remaining === 0 ? 'queue clear' : '';
                    resultEl.textContent = synced === 0
                        ? (queueSynced ? 'Rounds synced' : 'Nothing to sync')
                        : `${synced} game${synced === 1 ? '' : 's'} synced!`;
                    syncTimer = setTimeout(() => {
                        container.querySelector('#sync-section')?.classList.add('hidden');
                    }, 3000);
                } else {
                    resultEl.textContent = `${synced} synced, ${failed + (queueFailed ? 1 : 0)} failed. Retry?`;
                    syncBtn.disabled = false;
                }
                syncBtn.removeAttribute('aria-busy');
            });
        }

        function bindEvents() {
            bindHomeAndPlayers();
            bindResumeAndEnd();
            bindGameTypeTabs();
            bindStartAndChrome();
        }

        async function checkPendingSyncs() {
            try {
                const pendingGames = await getSyncPendingGames(shareCode);
                const queue = await getSyncQueue();
                const syncSection = container.querySelector('#sync-section');
                if (syncSection) {
                    if (pendingGames.length > 0 || queue.length > 0) {
                        syncSection.classList.remove('hidden');
                    } else {
                        syncSection.classList.add('hidden');
                    }
                }
            } catch (error) {
                logger.warn('lobby', `Failed to check pending syncs: ${error.message}`);
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
