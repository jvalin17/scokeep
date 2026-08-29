// Home screen — create or join playground

import { createPlayground, authPlayground, listRecentPlaygrounds, browsePlaygrounds, getPinHint } from '../api.js';
import { escapeHtml } from '../components/game-utils.js';

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
                    <button type="button" id="browse-rooms-btn" class="browse-toggle"><span aria-hidden="true">🔍</span> Browse Rooms</button>
                    <div id="browse-rooms" class="hidden">
                        <input type="text" id="browse-filter" placeholder="Filter by player name..." autocomplete="off" style="margin-bottom:8px;">
                        <div id="browse-list"></div>
                    </div>
                    <div id="recent-playgrounds"></div>
                    <input type="text" id="join-name" placeholder="Playground name"
                        maxlength="50" required autocomplete="off">
                    <input type="password" id="join-pin" placeholder="4-digit PIN"
                        maxlength="4" pattern="\\d{4}" inputmode="numeric" required>
                    <button type="submit" class="btn btn-primary">Enter</button>
                    <button type="button" id="forgot-pin" class="btn-text" style="font-size:0.8rem;">Forgot PIN?</button>
                    <p id="pin-hint-display" class="stats-muted hidden" style="font-size:0.85rem;"></p>
                    <p id="join-error" class="error hidden"></p>
                </form>

                <div id="howto-section" class="form hidden">
                    <div class="howto">
                        <h3>How to Play Judgement</h3>
                        <p>Judgement (Kachuful) is a trick-taking card game for 3–8 players.</p>
                        <div class="howto-steps">
                            <div class="howto-step">
                                <strong>1. Deal</strong>
                                <p>Cards are dealt in sets — 8 down to 1, then back up. Trump suit rotates: ♠ ♦ ♣ ♥</p>
                                <p>The dealer rotates clockwise each round. Example: if players are seated Alice, Bob, Charlie — Round 1: Charlie deals, Alice bids first → Bob → Charlie (dealer always bids last). Round 2: Alice deals, Bob bids first → Charlie → Alice.</p>
                            </div>
                            <div class="howto-step">
                                <strong>2. Bid</strong>
                                <p>Each player bids how many tricks they'll win this round. The last player (dealer) can't make the total equal the cards dealt (must-lose rule).</p>
                            </div>
                            <div class="howto-step">
                                <strong>3. Play</strong>
                                <p>Play your cards. Win tricks by playing the highest card of the led suit, or trump.</p>
                            </div>
                            <div class="howto-step">
                                <strong>4. Score</strong>
                                <p>Made your bid? Score points. Missed? Lose the same amount.</p>
                            </div>
                        </div>

                        <h4>Scoring</h4>
                        <table class="howto-table">
                            <thead><tr><th>Bid</th><th>Made</th><th>Missed</th></tr></thead>
                            <tbody>
                                <tr><td>0</td><td>+10</td><td>-10</td></tr>
                                <tr><td>1</td><td>+11</td><td>-11</td></tr>
                                <tr><td>2–8</td><td>+N × 10</td><td>-N × 10</td></tr>
                            </tbody>
                        </table>

                        <h3 style="margin-top:24px;">How to Use Scokeep</h3>
                        <div class="howto-steps">
                            <div class="howto-step">
                                <strong>1. Create a Room</strong>
                                <p>Give your group a name, a 4-digit PIN, and an optional PIN hint (in case you forget it later). Add player names and drag to set clockwise seating order.</p>
                                <p>Rooms are reusable — come back anytime with the same name + PIN. Other players can also join with the room name and PIN.</p>
                            </div>
                            <div class="howto-step">
                                <strong>2. Find Your Room</strong>
                                <p>On the Join tab, tap <strong>Browse All Rooms</strong> to see every room. Type a player's name to filter — find your room even if you forgot the room name. Pick yours with one tap.</p>
                                <p>Forgot your PIN? Tap <strong>Forgot PIN?</strong> to see the hint you set when creating the room.</p>
                            </div>
                            <div class="howto-step">
                                <strong>3. Pick Settings</strong>
                                <p>Choose game mode, scoring type (Ones or Zeros), number of sets, cards per round, appearance, and must-lose toggle. All configurable before the game starts.</p>
                            </div>
                            <div class="howto-step">
                                <strong>4. Enter Bids</strong>
                                <p>Tap each player's bid on the keypad. You can go back to previous players, and edit any bid on the confirm screen before starting the round.</p>
                                <p>In must-lose mode, the last player (dealer) cannot bid a number that makes the total equal the cards dealt.</p>
                            </div>
                            <div class="howto-step">
                                <strong>5. Play & Score</strong>
                                <p>After the round, tap how many tricks each player won. The last player's value auto-locks to match the total cards dealt.</p>
                                <p>Made a mistake after scoring? Tap <strong>Edit Hands</strong> on the scoreboard to re-enter hands and re-score the round — your bids stay intact. Or use <strong>Undo Last Round</strong> to start the round over completely.</p>
                            </div>
                            <div class="howto-step">
                                <strong>Takeover Anytime</strong>
                                <p>Anyone with the room name and PIN can open the app and take over scoring mid-game. Just join the room — the game resumes exactly where it left off.</p>
                            </div>
                            <div class="howto-step">
                                <strong>6. Extend or End</strong>
                                <p>After the last round, choose to add 1–4 more sets or see final scores. Sets alternate direction — if set 1 goes 8→1, set 2 goes 1→8.</p>
                                <p>You can end the game anytime. If you take a break, the game is recoverable for 30 minutes — just come back to your room.</p>
                            </div>
                            <div class="howto-step">
                                <strong>7. Stats & Insights</strong>
                                <p>View career awards (Sniper, Zero Master, High Roller), game history with expandable scoresheets, and score progression charts.</p>
                                <p>After 3 games, each player unlocks a <strong>Personality Card</strong> — tap to flip and see accuracy stats, bidding style, strengths, and fun facts.</p>
                            </div>
                            <div class="howto-step">
                                <strong>8. Install as App</strong>
                                <p>Scokeep is a PWA — tap "Add to Home Screen" in your browser to install it. Works like a native app with offline support and no browser chrome.</p>
                            </div>
                        </div>

                        <h4>Game Modes</h4>
                        <table class="howto-table">
                            <thead><tr><th>Mode</th><th>What You See</th><th>Best For</th></tr></thead>
                            <tbody>
                                <tr><td>Expert</td><td>Cards to deal only</td><td>Seasoned players who remember trump</td></tr>
                                <tr><td>Rookie</td><td>Trump suit shown</td><td>Regular players</td></tr>
                                <tr><td>Friendly</td><td>All bids, trump, scores</td><td>New players or teaching</td></tr>
                            </tbody>
                        </table>

                        <h4>Scoring Rules</h4>
                        <table class="howto-table">
                            <thead><tr><th>Rule</th><th>Bid 1 Made</th></tr></thead>
                            <tbody>
                                <tr><td>Ones (default)</td><td>+11 points</td></tr>
                                <tr><td>Zeros</td><td>+10 points</td></tr>
                            </tbody>
                        </table>
                        <p style="font-size:0.8rem;color:var(--text-muted);">Both rules: Bid 0 made = +10. Bid 2+ made = bid × 10. Miss = same amount negated.</p>
                    </div>
                </div>
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
            } catch { /* no recent playgrounds */ }
        }

        // Tab switching
        container.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                container.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                const target = tab.dataset.tab;
                container.querySelector('#create-form').classList.toggle('visible', target === 'create');
                container.querySelector('#create-form').classList.toggle('hidden', target !== 'create');
                container.querySelector('#join-form').classList.toggle('visible', target === 'join');
                container.querySelector('#join-form').classList.toggle('hidden', target !== 'join');
                container.querySelector('#howto-section').classList.toggle('visible', target === 'howto');
                container.querySelector('#howto-section').classList.toggle('hidden', target !== 'howto');
                if (target === 'join') loadRecent();
            });
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
            } catch {
                hintEl.textContent = 'Room not found';
                hintEl.classList.remove('hidden');
            }
        });

        // Browse all rooms
        let allRooms = null;
        const browseBtn = container.querySelector('#browse-rooms-btn');
        const browsePanel = container.querySelector('#browse-rooms');
        const browseFilter = container.querySelector('#browse-filter');
        const browseList = container.querySelector('#browse-list');

        const recentEl = container.querySelector('#recent-playgrounds');

        browseBtn.addEventListener('click', async () => {
            if (!browsePanel.classList.contains('hidden')) {
                browsePanel.classList.add('hidden');
                if (recentEl) recentEl.classList.remove('hidden');
                return;
            }
            if (recentEl) recentEl.classList.add('hidden');
            if (!allRooms) {
                try {
                    const data = await browsePlaygrounds();
                    allRooms = data.rooms || [];
                } catch { allRooms = []; }
            }
            browseFilter.value = '';
            renderBrowseList(allRooms);
            browsePanel.classList.remove('hidden');
            browseFilter.focus();
        });

        browseFilter.addEventListener('input', () => {
            const q = browseFilter.value.toLowerCase();
            const filtered = (allRooms || []).filter(r => {
                const nameMatch = r.name.toLowerCase().includes(q);
                const playerMatch = (r.players || []).some(p => p.toLowerCase().includes(q));
                return nameMatch || playerMatch;
            });
            renderBrowseList(filtered);
        });

        function renderBrowseList(rooms) {
            if (!rooms.length) {
                browseList.innerHTML = allRooms && allRooms.length
                    ? '<p class="stats-muted" style="padding:8px;">No rooms found</p>'
                    : '<p class="stats-muted" style="padding:8px;">No rooms yet — create one!</p>';
                return;
            }
            browseList.className = 'browse-list';
            browseList.innerHTML = rooms
                .map(r => `<button type="button" class="recent-item browse-item" data-name="${escapeHtml(r.name)}">${escapeHtml(r.name)}</button>`)
                .join('');
            browseList.querySelectorAll('.browse-item').forEach(btn => {
                btn.addEventListener('click', () => {
                    container.querySelector('#join-name').value = btn.dataset.name;
                    browsePanel.classList.add('hidden');
                    if (recentEl) recentEl.classList.remove('hidden');
                    container.querySelector('#join-pin').focus();
                });
            });
        }

        // Add player button
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
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Creating...';
            submitBtn.disabled = true;

            try {
                const playground = await createPlayground(name, pin, players, pinHint);
                await authPlayground(name, pin);
                state.playground = playground;
                navigate(`playground/${playground.share_code}`);
            } catch (error) {
                errorElement.textContent = error.message;
                errorElement.classList.remove('hidden');
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
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
            const joinOriginal = joinBtn.textContent;
            joinBtn.textContent = 'Joining...';
            joinBtn.disabled = true;

            try {
                const playground = await authPlayground(name, pin);
                state.playground = playground;
                navigate(`playground/${playground.share_code}`);
            } catch (error) {
                errorElement.textContent = error.message;
                errorElement.classList.remove('hidden');
                joinBtn.textContent = joinOriginal;
                joinBtn.disabled = false;
            }
        });
    },

    unmount() {},
};
