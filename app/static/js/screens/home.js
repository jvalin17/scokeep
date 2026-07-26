// Home screen — create or join playground

import { createPlayground, authPlayground, listRecentPlaygrounds } from '../api.js';

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
                </div>

                <form id="create-form" class="form visible">
                    <input type="text" id="create-name" placeholder="Playground name"
                        maxlength="50" required autocomplete="off">
                    <input type="text" id="create-pin" placeholder="4-digit PIN"
                        maxlength="4" pattern="\\d{4}" inputmode="numeric" required>
                    <div id="player-list" class="player-list">
                        <div class="player-input-row">
                            <input type="text" placeholder="Player 1" class="player-name"
                                maxlength="20" required autocomplete="off">
                        </div>
                        <div class="player-input-row">
                            <input type="text" placeholder="Player 2" class="player-name"
                                maxlength="20" required autocomplete="off">
                        </div>
                    </div>
                    <button type="button" id="add-player" class="btn-text">+ Add player</button>
                    <button type="submit" class="btn btn-primary">Create Playground</button>
                    <p id="create-error" class="error hidden"></p>
                </form>

                <form id="join-form" class="form hidden">
                    <div id="recent-playgrounds"></div>
                    <input type="text" id="join-name" placeholder="Playground name"
                        maxlength="50" required autocomplete="off">
                    <input type="text" id="join-pin" placeholder="4-digit PIN"
                        maxlength="4" pattern="\\d{4}" inputmode="numeric" required>
                    <button type="submit" class="btn btn-primary">Enter</button>
                    <p id="join-error" class="error hidden"></p>
                </form>
            </div>
        `;

        // Load recent playgrounds
        async function loadRecent() {
            try {
                const { names } = await listRecentPlaygrounds();
                const recentEl = container.querySelector('#recent-playgrounds');
                if (names.length > 0) {
                    recentEl.innerHTML = `
                        <div class="recent-list">
                            ${names.map(name => `<button type="button" class="recent-item">${name}</button>`).join('')}
                        </div>
                    `;
                    recentEl.querySelectorAll('.recent-item').forEach(btn => {
                        btn.addEventListener('click', () => {
                            container.querySelector('#join-name').value = btn.textContent;
                            container.querySelector('#join-pin').focus();
                        });
                    });
                }
            } catch (e) { console.warn('Failed to load recent:', e.message); }
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
                if (target === 'join') loadRecent();
            });
        });

        // Add player button
        let playerCount = 2;
        container.querySelector('#add-player').addEventListener('click', () => {
            if (playerCount >= 8) return;
            playerCount++;
            const row = document.createElement('div');
            row.className = 'player-input-row';
            row.innerHTML = `
                <input type="text" placeholder="Player ${playerCount}" class="player-name"
                    maxlength="20" autocomplete="off">
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
                const playground = await createPlayground(name, pin, players);
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
