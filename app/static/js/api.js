// API client — all fetch() calls to backend
// Every function checks response.ok before returning

const BASE = '/api';

async function request(method, path, body = null) {
    console.log(`[api] ${method} ${path}`, body || '');
    const options = {
        method,
        headers: {},
        credentials: 'same-origin',
    };
    if (body) {
        options.headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(body);
    }
    const response = await fetch(`${BASE}${path}`, options);
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        const detail = error.detail;
        const message = typeof detail === 'string' ? detail : JSON.stringify(detail);
        console.error(`[api] ${method} ${path} → ${response.status}: ${message}`);
        throw new Error(message || `HTTP ${response.status}`);
    }
    const data = await response.json();
    console.log(`[api] ${method} ${path} → ${response.status}`);
    return data;
}

// Re-sync: fetch game state and navigate to correct screen
export async function resyncGame(gameId) {
    const game = await request('GET', `/game/${gameId}`);
    const routes = {
        bidding: `bid/${gameId}`,
        playing: `play/${gameId}`,
        round_end: `roundend/${gameId}`,
        scoreboard: `scoreboard/${gameId}`,
        final: `final/${gameId}`,
    };
    const route = routes[game.phase] || `scoreboard/${gameId}`;
    window.location.hash = route;
    return game;
}

// Playground
export function listRecentPlaygrounds() {
    return request('GET', '/playground/recent');
}

export function createPlayground(name, pin, players) {
    return request('POST', '/playground', { name, pin, players });
}

export function authPlayground(name, pin) {
    return request('POST', '/playground/auth', { name, pin });
}

export function getPlayground(shareCode) {
    return request('GET', `/playground/${shareCode}`);
}

export function getPlaygroundStats(shareCode) {
    return request('GET', `/playground/${shareCode}/stats`);
}

// Game
export function createGame(playgroundId, players, settings = {}) {
    return request('POST', '/game', {
        playground_id: playgroundId,
        players,
        settings,
    });
}

export function getGame(gameId) {
    return request('GET', `/game/${gameId}`);
}

export function getActiveGame(playgroundId) {
    return request('GET', `/game/active/${playgroundId}`);
}

export function nextRound(gameId) {
    return request('POST', `/game/${gameId}/next-round`);
}

export function endGame(gameId) {
    return request('POST', `/game/${gameId}/end`);
}

// Round
export function submitBid(gameId, playerIndex, value) {
    return request('POST', `/game/${gameId}/bid`, {
        player_index: playerIndex,
        value,
    });
}

export function getBids(gameId) {
    return request('GET', `/game/${gameId}/bids`);
}

export function editBid(gameId, playerIndex, value) {
    return request('PATCH', `/game/${gameId}/bid/${playerIndex}`, { value });
}

export function startRound(gameId) {
    return request('POST', `/game/${gameId}/start-round`);
}

export function enterRoundEnd(gameId) {
    return request('POST', `/game/${gameId}/enter-round-end`);
}

export function submitHands(gameId, playerIndex, value) {
    return request('POST', `/game/${gameId}/hands`, {
        player_index: playerIndex,
        value,
    });
}

export function endRound(gameId) {
    return request('POST', `/game/${gameId}/end-round`);
}

// Scoreboard
export function getScoreboard(gameId) {
    return request('GET', `/game/${gameId}/scoreboard`);
}

export function getHistory(gameId) {
    return request('GET', `/game/${gameId}/history`);
}

export function undoRound(gameId) {
    return request('POST', `/game/${gameId}/undo`);
}
