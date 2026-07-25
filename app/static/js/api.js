// API client — all fetch() calls to backend
// Every function checks response.ok before returning

const BASE = '/api';

async function request(method, path, body = null) {
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
        throw new Error(error.detail || `HTTP ${response.status}`);
    }
    return response.json();
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
