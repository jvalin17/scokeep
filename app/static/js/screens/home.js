// Home screen — create or join playground, or start a quick local game

import { createPlayground, authPlayground, listRecentPlaygrounds, browsePlaygrounds, getPinHint } from '../api.js';
import { createGame } from '../game-api.js';
import { escapeHtml } from '../components/game-utils.js';
import { renderSettingsGrid, readSettings, updateCardsDropdown } from '../components/game-settings.js';
import { saveRoom, getAllRooms, getRoom, getFinishedGames } from '../engine/store.js';
import { createVerifier, checkPin, isLocked, checkAttempt } from '../engine/pin-verifier.js';

// ─── helpers ────────────────────────────────────────────────────────────────

/** Cache a room + PBKDF2 verifier in IDB after successful online auth. */
async function _cacheRoom(playground, pin) {
    const verifier = await createVerifier(pin);
    await saveRoom({
        share_code: playground.share_code,
        name: playground.name,
        players: playground.players,
        pin_verifier: verifier,
        attempts: 0,
        locked_until: null,
        cached_at: new Date().toISOString(),
    });
}

/** Return the How To section HTML (static content, extracted to reduce mount() size). */
function _howtoHtml() {
    return `<div id="howto-section" class="form hidden">
        <div class="howto">
            <h3>How to Play Judgement</h3>
            <p>Judgement (Kachuful) is a trick-taking card game for 3-8 players.</p>
            <div class="howto-steps">
                <div class="howto-step"><strong>1. Deal</strong><p>Cards are dealt in sets - 8 down to 1, then back up. Trump suit rotates.</p></div>
                <div class="howto-step"><strong>2. Bid</strong><p>Each player bids how many tricks they'll win. Dealer can't make total equal cards dealt (must-lose).</p></div>
                <div class="howto-step"><strong>3. Play</strong><p>Play your cards. Win tricks by playing the highest card of the led suit, or trump.</p></div>
                <div class="howto-step"><strong>4. Score</strong><p>Made your bid? Score points. Missed? Lose the same amount.</p></div>
            </div>
            <h4>Scoring</h4>
            <table class="howto-table"><thead><tr><th>Bid</th><th>Made</th><th>Missed</th></tr></thead>
            <tbody><tr><td>0</td><td>+10</td><td>-10</td></tr><tr><td>1</td><td>+11</td><td>-11</td></tr><tr><td>2-8</td><td>+N x 10</td><td>-N x 10</td></tr></tbody></table>
            <h3 style="margin-top:24px;">How to Use Scokeep</h3>
            <div class="howto-steps">
                <div class="howto-step"><strong>1. Create a Room</strong><p>Give your group a name, a 4-digit PIN, and an optional PIN hint. Add player names and drag to set seating order. Rooms are reusable.</p></div>
                <div class="howto-step"><strong>2. Find Your Room</strong><p>On the Join tab, tap Browse All Rooms. Type a player's name to filter. Forgot your PIN? Tap Forgot PIN? to see the hint.</p></div>
                <div class="howto-step"><strong>3. Pick Settings</strong><p>Choose game mode, scoring type, number of sets, cards per round, appearance, and must-lose toggle.</p></div>
                <div class="howto-step"><strong>4. Enter Bids</strong><p>Tap each player's bid on the keypad. Edit any bid on the confirm screen before starting the round.</p></div>
                <div class="howto-step"><strong>5. Play & Score</strong><p>Tap how many tricks each player won. Edit Hands to re-enter and re-score. Undo Last Round to start over.</p></div>
                <div class="howto-step"><strong>Takeover Anytime</strong><p>Anyone with the room name and PIN can take over scoring mid-game.</p></div>
                <div class="howto-step"><strong>6. Extend or End</strong><p>Add 1-4 more sets or see final scores. Sets alternate direction. Game recoverable for 30 minutes.</p></div>
                <div class="howto-step"><strong>7. Stats & Insights</strong><p>Career awards, game history, score charts. After first game, each player unlocks a Personality Card.</p></div>
                <div class="howto-step"><strong>8. Install as App</strong><p>Scokeep is a PWA - tap "Add to Home Screen" for offline support and no browser chrome.</p></div>
                <div class="howto-step"><strong>9. Post-Game Awards</strong><p>Fun titles based on how you played - 40 possible titles. Every player gets at least one.</p></div>
                <div class="howto-step"><strong>10. Career Records</strong><p>Lifetime achievements: Sniper, Zero Master, High Roller, All-in, Perfect Set, Sweep, Hot Hand, Iron Wall, Biggest Bid, Comeback King, Set Champion, Set Disaster, Heartbreaker, Triple Crown.</p></div>
            </div>
            <h4>Game Modes</h4>
            <table class="howto-table"><thead><tr><th>Mode</th><th>What You See</th><th>Best For</th></tr></thead>
            <tbody><tr><td>Expert</td><td>Cards to deal only</td><td>Seasoned players</td></tr><tr><td>Rookie</td><td>Trump suit shown</td><td>Regular players</td></tr><tr><td>Friendly</td><td>All bids, trump, scores</td><td>New players</td></tr></tbody></table>
            <h4>Scoring Rules</h4>
            <table class="howto-table"><thead><tr><th>Rule</th><th>Bid 1 Made</th></tr></thead>
            <tbody><tr><td>Ones (default)</td><td>+11 points</td></tr><tr><td>Zeros</td><td>+10 points</td></tr></tbody></table>
            <p style="font-size:0.8rem;color:var(--text-muted);">Both rules: Bid 0 made = +10. Bid 2+ made = bid x 10. Miss = same amount negated.</p>
        </div>
    </div>`;
}

/** Disable a button with loading text, return a restore function. */
function _withLoading(button, loadingText) {
    const originalText = button.textContent;
    button.textContent = loadingText;
    button.disabled = true;
    return () => {
        button.textContent = originalText;
        button.disabled = false;
    };
}

export const homeScreen = {
    mount(container, state, { navigate }) {
        document.body.setAttribute('data-phase', 'home');
        document.body.setAttribute('data-appearance', 'standard');
        container.innerHTML = `
            <div class="home">
                <h1 class="logo">Scokeep</h1>
                <p class="tagline">Score tracker for card games</p>

                <div class="tabs">
                    <button class="tab active" data-tab="create">Create</button>
                    <button class="tab" data-tab="join">Join</button>
                    <button class="tab" data-tab="quick">Quick Game <span id="quick-badge" class="hidden" style="background:var(--accent);color:#fff;border-radius:10px;padding:1px 6px;font-size:0.7rem;vertical-align:middle;"></span></button>
                    <button class="tab" data-tab="howto">How To</button>
                </div>

                <form id="create-form" class="form visible">
                    <input type="text" id="create-name" placeholder="Playground name"
                        maxlength="50" required autocomplete="off">
                    <input type="password" id="create-pin" placeholder="4-digit PIN"
                        maxlength="4" pattern="\\d{4}" inputmode="numeric" required>
                    <input type="text" id="create-hint" placeholder="PIN hint (optional, e.g. birthday)"
                        maxlength="100" autocomplete="off">
                    <div id="player-list" class="player-list">
                        <div class="player-input-row">
                            <input type="text" placeholder="Player 1" class="player-name"
                                maxlength="15" required autocomplete="off">
                        </div>
                        <div class="player-input-row">
                            <input type="text" placeholder="Player 2" class="player-name"
                                maxlength="15" required autocomplete="off">
                        </div>
                    </div>
                    <button type="button" id="add-player" class="btn-text">+ Add player</button>
                    <button type="submit" class="btn btn-primary">Create Playground</button>
                    <p id="create-error" class="error hidden"></p>
                </form>

                <form id="join-form" class="form hidden">
                    <div class="room-finder">
                        <div class="room-finder-header">
                            <span class="room-finder-label">Rooms</span>
                            <button type="button" id="browse-rooms-btn" class="browse-toggle">Browse all</button>
                        </div>
                        <div id="recent-playgrounds" class="room-finder-list"></div>
                        <div id="browse-rooms" class="hidden">
                            <input type="text" id="browse-filter-room" placeholder="Search by room name..." autocomplete="off" class="room-finder-search">
                            <input type="text" id="browse-filter-player" placeholder="Search by player name..." autocomplete="off" class="room-finder-search">
                            <div id="browse-list" class="room-finder-list"></div>
                        </div>
                    </div>
                    <input type="text" id="join-name" placeholder="Playground name"
                        maxlength="50" required autocomplete="off">
                    <input type="password" id="join-pin" placeholder="4-digit PIN"
                        maxlength="4" pattern="\\d{4}" inputmode="numeric" required>
                    <button type="submit" class="btn btn-primary">Enter</button>
                    <button type="button" id="forgot-pin" class="btn-text" style="font-size:0.8rem;">Forgot PIN?</button>
                    <p id="pin-hint-display" class="stats-muted hidden" style="font-size:0.85rem;"></p>
                    <p id="join-error" class="error hidden"></p>
                </form>

                <div id="quick-form" class="form hidden">
                    <div id="quick-player-list" class="player-list">
                        <div class="player-input-row">
                            <input type="text" placeholder="Player 1" class="quick-player-name"
                                maxlength="15" required autocomplete="off">
                        </div>
                        <div class="player-input-row">
                            <input type="text" placeholder="Player 2" class="quick-player-name"
                                maxlength="15" required autocomplete="off">
                        </div>
                    </div>
                    <button type="button" id="quick-add-player" class="btn-text">+ Add player</button>

                    <div class="room-finder" style="margin-top:12px;">
                        <div class="room-finder-header">
                            <span class="room-finder-label">Rooms</span>
                            <button type="button" id="quick-browse-btn" class="browse-toggle">Browse all</button>
                        </div>
                        <div id="quick-room-list" class="room-finder-list"></div>
                        <div id="quick-browse-rooms" class="hidden">
                            <input type="text" id="quick-browse-filter" placeholder="Search by room or player name..." autocomplete="off" class="room-finder-search">
                            <div id="quick-browse-list" class="room-finder-list"></div>
                        </div>
                        <div id="quick-room-pin-section" class="hidden" style="margin-top:8px;">
                            <p id="quick-room-selected" style="font-weight:600;margin-bottom:6px;"></p>
                            <div style="display:flex;gap:8px;align-items:center;">
                                <input type="password" id="quick-room-pin" placeholder="Enter room PIN"
                                    maxlength="4" inputmode="numeric" pattern="[0-9]*" autocomplete="off" style="flex:1;">
                                <button type="button" id="quick-room-verify" class="btn btn-primary" style="padding:8px 16px;">Verify</button>
                            </div>
                            <p id="quick-room-error" class="error hidden" style="margin-top:4px;"></p>
                            <p id="quick-room-success" class="hidden" style="margin-top:4px;color:var(--success,#22c55e);font-size:0.85rem;"></p>
                            <button type="button" id="quick-room-clear" class="btn-text" style="margin-top:4px;font-size:0.8rem;">Clear selection</button>
                        </div>
                    </div>

                    <div style="margin-top:12px;">
                        ${renderSettingsGrid({ prefix: 'quick-setting', playerCount: 2 })}
                    </div>

                    <button type="button" id="quick-start" class="btn btn-primary" style="margin-top:16px;">Start Game</button>
                    <p id="quick-error" class="error hidden"></p>
                </div>

                ${_howtoHtml()}
            </div>
        `;

        // Load recent playgrounds
        async function loadRecent() {
            try {
                const { names } = await listRecentPlaygrounds();
                const recentEl = container.querySelector('#recent-playgrounds');
                if (recentEl && names.length > 0) {
                    recentEl.innerHTML = `
                        <div class="recent-list">
                            ${names.map(name => `<button type="button" class="recent-item">${escapeHtml(name)}</button>`).join('')}
                        </div>
                    `;
                    recentEl.querySelectorAll('.recent-item').forEach(btn => {
                        btn.addEventListener('click', () => {
                            container.querySelector('#join-name').value = btn.textContent;
                            container.querySelector('#join-pin').focus();
                        });
                    });
                }
            } catch (error) { console.warn('Failed to load recent playgrounds:', error); }
        }

        // Tab switching
        const TAB_PANELS = ['create', 'join', 'quick', 'howto'];
        container.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                container.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                const target = tab.dataset.tab;
                const panelIds = {
                    create: '#create-form',
                    join: '#join-form',
                    quick: '#quick-form',
                    howto: '#howto-section',
                };
                TAB_PANELS.forEach(name => {
                    const el = container.querySelector(panelIds[name]);
                    if (!el) return;
                    el.classList.toggle('visible', name === target);
                    el.classList.toggle('hidden', name !== target);
                });
                if (target === 'join') loadRecent();
                if (target === 'quick') loadCachedRooms();
            });
        });

        // Quick Game — pending sync badge
        async function updateSyncBadge() {
            try {
                const finished = await getFinishedGames(100);
                const pendingCount = finished.filter(g => g.sync_pending === true).length;
                const badge = container.querySelector('#quick-badge');
                if (badge) {
                    if (pendingCount > 0) {
                        badge.textContent = `${pendingCount} pending`;
                        badge.classList.remove('hidden');
                    } else {
                        badge.classList.add('hidden');
                    }
                }
            } catch (error) { console.warn('Badge update failed:', error); }
        }
        updateSyncBadge().catch(() => {});

        // Quick Game — room selection handler
        let selectedRoomCode = null;
        let selectedRoomName = null;
        let linkedRoom = null;
        let allCachedRooms = [];

        function selectQuickRoom(shareCode, label) {
            selectedRoomCode = shareCode;
            selectedRoomName = label;
            linkedRoom = null;
            // Highlight selected across both lists
            container.querySelectorAll('.quick-room-item').forEach(b =>
                b.classList.toggle('active', b.dataset.code === shareCode)
            );
            // Show PIN section
            container.querySelector('#quick-room-selected').textContent = label;
            container.querySelector('#quick-room-pin-section').classList.remove('hidden');
            container.querySelector('#quick-room-pin').value = '';
            container.querySelector('#quick-room-error').classList.add('hidden');
            container.querySelector('#quick-room-success').classList.add('hidden');
            container.querySelector('#quick-room-pin').focus();
        }

        function renderRoomButtons(listEl, rooms) {
            if (!rooms.length) {
                listEl.innerHTML = '<p class="stats-muted" style="padding:8px;">No rooms found</p>';
                return;
            }
            listEl.innerHTML = rooms.map(room =>
                `<button type="button" class="recent-item quick-room-item browse-item" data-code="${escapeHtml(room.share_code)}">${escapeHtml(room.name)}</button>`
            ).join('');
            listEl.querySelectorAll('.quick-room-item').forEach(btn => {
                btn.addEventListener('click', () => selectQuickRoom(btn.dataset.code, btn.textContent));
                if (btn.dataset.code === selectedRoomCode) btn.classList.add('active');
            });
        }

        // Load cached rooms (rooms user has joined before)
        async function loadCachedRooms() {
            try {
                allCachedRooms = await getAllRooms();
                const listEl = container.querySelector('#quick-room-list');
                if (!allCachedRooms.length) {
                    listEl.innerHTML = '';
                    return;
                }
                renderRoomButtons(listEl, allCachedRooms);
            } catch (error) { console.warn('Failed to load cached rooms:', error); }
        }

        // Browse all — fetch from server if online, else use cached
        const quickBrowseBtn = container.querySelector('#quick-browse-btn');
        const quickBrowsePanel = container.querySelector('#quick-browse-rooms');
        const quickBrowseFilter = container.querySelector('#quick-browse-filter');
        const quickBrowseList = container.querySelector('#quick-browse-list');
        let quickAllRooms = null;

        quickBrowseBtn.addEventListener('click', async () => {
            if (!quickBrowsePanel.classList.contains('hidden')) {
                quickBrowsePanel.classList.add('hidden');
                quickBrowseBtn.textContent = 'Browse all';
                return;
            }
            if (!quickAllRooms) {
                try {
                    const data = await browsePlaygrounds();
                    quickAllRooms = data.rooms || [];
                } catch (error) {
                    console.warn('Browse rooms failed (offline fallback):', error);
                    quickAllRooms = allCachedRooms;
                }
            }
            quickBrowseFilter.value = '';
            renderRoomButtons(quickBrowseList, quickAllRooms);
            quickBrowsePanel.classList.remove('hidden');
            quickBrowseBtn.textContent = 'Close ×';
            quickBrowseFilter.focus();
        });

        quickBrowseFilter.addEventListener('input', () => {
            const query = quickBrowseFilter.value.toLowerCase();
            const filtered = (quickAllRooms || []).filter(room =>
                room.name.toLowerCase().includes(query) ||
                (room.players || []).some(p => p.toLowerCase().includes(query))
            );
            renderRoomButtons(quickBrowseList, filtered);
        });

        // Clear room selection
        container.querySelector('#quick-room-clear').addEventListener('click', () => {
            selectedRoomCode = null;
            selectedRoomName = null;
            linkedRoom = null;
            container.querySelector('#quick-room-pin-section').classList.add('hidden');
            container.querySelectorAll('.quick-room-item').forEach(b => b.classList.remove('active'));
        });

        // Quick Game — PIN verification
        container.querySelector('#quick-room-verify').addEventListener('click', async () => {
            const shareCode = selectedRoomCode;
            const pin = container.querySelector('#quick-room-pin').value;
            const errorEl = container.querySelector('#quick-room-error');
            const successEl = container.querySelector('#quick-room-success');
            errorEl.classList.add('hidden');
            successEl.classList.add('hidden');

            if (!shareCode || !pin) return;

            try {
                let room = await getRoom(shareCode);

                // Room not cached — try online auth and cache it
                if (!room || !room.pin_verifier) {
                    try {
                        const serverRoom = await authPlayground(selectedRoomName, pin);
                        await _cacheRoom(serverRoom, pin);
                        room = await getRoom(shareCode);
                    } catch {
                        errorEl.textContent = 'Room not cached — connect to internet to verify';
                        errorEl.classList.remove('hidden');
                        return;
                    }
                }

                if (isLocked(room)) {
                    const minutes = Math.ceil((room.locked_until - Date.now()) / 60000);
                    errorEl.textContent = `Too many attempts. Try again in ${minutes} min`;
                    errorEl.classList.remove('hidden');
                    return;
                }

                const pinMatch = await checkPin(pin, room.pin_verifier);
                const attempt = checkAttempt(room, pinMatch);
                await saveRoom(room); // persist attempt counter

                if (!pinMatch) {
                    errorEl.textContent = attempt.allowed ? 'Wrong PIN' : 'Wrong PIN — locked out';
                    errorEl.classList.remove('hidden');
                    container.querySelector('#quick-room-pin').value = '';
                    return;
                }

                // PIN correct — auto-fill players
                linkedRoom = shareCode;
                successEl.textContent = `✓ ${room.name} — ${room.players.length} players loaded`;
                successEl.classList.remove('hidden');

                const playerList = container.querySelector('#quick-player-list');
                playerList.innerHTML = '';
                quickPlayerCount = room.players.length;
                room.players.forEach((playerName, index) => {
                    const row = document.createElement('div');
                    row.className = 'player-input-row';
                    const input = document.createElement('input');
                    input.type = 'text';
                    input.placeholder = `Player ${index + 1}`;
                    input.className = 'quick-player-name';
                    input.maxLength = 15;
                    input.required = true;
                    input.autocomplete = 'off';
                    input.value = playerName;
                    row.appendChild(input);
                    playerList.appendChild(row);
                });
                updateCardsDropdown(container, 'quick-setting', quickPlayerCount);
            } catch (error) {
                errorEl.textContent = error.message;
                errorEl.classList.remove('hidden');
            }
        });

        // Forgot PIN — show hint
        container.querySelector('#forgot-pin').addEventListener('click', async () => {
            const name = container.querySelector('#join-name').value.trim();
            const hintEl = container.querySelector('#pin-hint-display');
            if (!name) {
                hintEl.textContent = 'Enter the room name first';
                hintEl.classList.remove('hidden');
                return;
            }
            try {
                const data = await getPinHint(name);
                hintEl.textContent = data.hint
                    ? `Hint: ${data.hint}`
                    : 'No hint was set for this room';
                hintEl.classList.remove('hidden');
            } catch (error) {
                console.warn('PIN hint lookup failed:', error);
                hintEl.textContent = 'Room not found';
                hintEl.classList.remove('hidden');
            }
        });

        // Room finder — browse all rooms
        let allRooms = null;
        const browseBtn = container.querySelector('#browse-rooms-btn');
        const browsePanel = container.querySelector('#browse-rooms');
        const filterRoom = container.querySelector('#browse-filter-room');
        const filterPlayer = container.querySelector('#browse-filter-player');
        const browseList = container.querySelector('#browse-list');
        const recentEl = container.querySelector('#recent-playgrounds');

        browseBtn.addEventListener('click', async () => {
            if (!browsePanel.classList.contains('hidden')) {
                browsePanel.classList.add('hidden');
                browseBtn.textContent = 'Browse all';
                if (recentEl) recentEl.classList.remove('hidden');
                return;
            }
            if (recentEl) recentEl.classList.add('hidden');
            if (!allRooms) {
                try {
                    const data = await browsePlaygrounds();
                    allRooms = data.rooms || [];
                } catch (error) { console.warn('Browse rooms failed:', error); allRooms = []; }
            }
            filterRoom.value = '';
            filterPlayer.value = '';
            renderBrowseList(allRooms);
            browsePanel.classList.remove('hidden');
            browseBtn.textContent = 'Close ×';
            filterRoom.focus();
        });

        function applyFilters() {
            const roomQuery = filterRoom.value.toLowerCase();
            const playerQuery = filterPlayer.value.toLowerCase();
            const filtered = (allRooms || []).filter(r => {
                const roomMatch = !roomQuery || r.name.toLowerCase().includes(roomQuery);
                const playerMatch = !playerQuery || (r.players || []).some(p => p.toLowerCase().includes(playerQuery));
                return roomMatch && playerMatch;
            });
            renderBrowseList(filtered);
        }

        filterRoom.addEventListener('input', applyFilters);
        filterPlayer.addEventListener('input', applyFilters);

        function renderBrowseList(rooms) {
            if (!rooms.length) {
                browseList.innerHTML = allRooms && allRooms.length
                    ? '<p class="stats-muted" style="padding:8px;">No rooms found</p>'
                    : '<p class="stats-muted" style="padding:8px;">No rooms yet — create one!</p>';
                return;
            }
            browseList.innerHTML = rooms
                .map(r => `<button type="button" class="recent-item browse-item" data-name="${escapeHtml(r.name)}">${escapeHtml(r.name)}</button>`)
                .join('');
            browseList.querySelectorAll('.browse-item').forEach(btn => {
                btn.addEventListener('click', () => {
                    container.querySelector('#join-name').value = btn.dataset.name;
                    browsePanel.classList.add('hidden');
                    browseBtn.textContent = 'Browse all';
                    if (recentEl) recentEl.classList.remove('hidden');
                    container.querySelector('#join-pin').focus();
                });
            });
        }

        // Quick Game — add player
        let quickPlayerCount = 2;
        container.querySelector('#quick-add-player').addEventListener('click', () => {
            if (quickPlayerCount >= 8) return;
            quickPlayerCount++;
            const row = document.createElement('div');
            row.className = 'player-input-row';
            row.innerHTML = `
                <input type="text" placeholder="Player ${quickPlayerCount}" class="quick-player-name"
                    maxlength="15" autocomplete="off">
                <button type="button" class="btn-remove" title="Remove">&times;</button>
            `;
            row.querySelector('.btn-remove').addEventListener('click', () => {
                row.remove();
                quickPlayerCount--;
                updateCardsDropdown(container, 'quick-setting', quickPlayerCount);
            });
            container.querySelector('#quick-player-list').appendChild(row);
            updateCardsDropdown(container, 'quick-setting', quickPlayerCount);
        });

        // Quick Game — start
        container.querySelector('#quick-start').addEventListener('click', async () => {
            const errorElement = container.querySelector('#quick-error');
            errorElement.classList.add('hidden');

            const players = Array.from(container.querySelectorAll('.quick-player-name'))
                .map(input => input.value.trim())
                .filter(name => name.length > 0);

            if (players.length < 2) {
                errorElement.textContent = 'At least 2 players required';
                errorElement.classList.remove('hidden');
                return;
            }

            const settings = readSettings(container, 'quick-setting');
            // Clamp cards to max for actual player count
            const maxCards = Math.floor(52 / Math.max(players.length, 2));
            settings.rounds_per_set = Math.min(settings.rounds_per_set, maxCards);
            if (linkedRoom) {
                settings.linked_room = linkedRoom;
            }

            const startBtn = container.querySelector('#quick-start');
            const restoreBtn = _withLoading(startBtn, 'Starting...');

            try {
                const game = await createGame(players, settings);
                navigate(`bid/${game.id}`);
            } catch (error) {
                errorElement.textContent = error.message;
                errorElement.classList.remove('hidden');
                restoreBtn();
            }
        });

        // Create playground — add player button
        let playerCount = 2;
        container.querySelector('#add-player').addEventListener('click', () => {
            if (playerCount >= 8) return;
            playerCount++;
            const row = document.createElement('div');
            row.className = 'player-input-row';
            row.innerHTML = `
                <input type="text" placeholder="Player ${playerCount}" class="player-name"
                    maxlength="15" autocomplete="off">
                <button type="button" class="btn-remove" title="Remove">&times;</button>
            `;
            row.querySelector('.btn-remove').addEventListener('click', () => {
                row.remove();
                playerCount--;
            });
            container.querySelector('#player-list').appendChild(row);
        });

        // Create playground
        container.querySelector('#create-form').addEventListener('submit', async (event) => {
            event.preventDefault();
            const errorElement = container.querySelector('#create-error');
            errorElement.classList.add('hidden');

            const name = container.querySelector('#create-name').value.trim();
            const pin = container.querySelector('#create-pin').value;
            const pinHint = container.querySelector('#create-hint').value.trim() || null;
            const players = Array.from(container.querySelectorAll('.player-name'))
                .map(input => input.value.trim())
                .filter(name => name.length > 0);

            if (players.length < 2) {
                errorElement.textContent = 'At least 2 players required';
                errorElement.classList.remove('hidden');
                return;
            }

            const submitBtn = container.querySelector('#create-form button[type="submit"]');
            const restoreBtn = _withLoading(submitBtn, 'Creating...');

            try {
                const playground = await createPlayground(name, pin, players, pinHint);
                await authPlayground(name, pin);
                state.playground = playground;

                try { await _cacheRoom(playground, pin); }
                catch (cacheError) { console.warn('IDB cache failed:', cacheError); }

                navigate(`playground/${playground.share_code}`);
            } catch (error) {
                errorElement.textContent = error.message;
                errorElement.classList.remove('hidden');
                restoreBtn();
            }
        });

        // Join / return to playground
        container.querySelector('#join-form').addEventListener('submit', async (event) => {
            event.preventDefault();
            const errorElement = container.querySelector('#join-error');
            errorElement.classList.add('hidden');

            const name = container.querySelector('#join-name').value.trim();
            const pin = container.querySelector('#join-pin').value;

            const joinBtn = container.querySelector('#join-form button[type="submit"]');
            const restoreBtn = _withLoading(joinBtn, 'Joining...');

            try {
                const playground = await authPlayground(name, pin);
                state.playground = playground;

                try { await _cacheRoom(playground, pin); }
                catch (cacheError) { console.warn('IDB cache failed:', cacheError); }

                navigate(`playground/${playground.share_code}`);
            } catch (error) {
                errorElement.textContent = error.message;
                errorElement.classList.remove('hidden');
                restoreBtn();
            }
        });
    },

    unmount() {},
};
