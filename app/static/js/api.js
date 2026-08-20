// API client — all fetch() calls to backend

import { logger } from './components/logger.js';

const BASE = '/api';

async function request(method, path, body = null) {
    logger.apiCall(method, path, body);
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
    if (response.status === 401) {
        logger.apiError(method, path, 401, 'Session expired');
        window.location.hash = '';
        throw new Error('Session expired — please re-enter your PIN');
    }
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        const detail = error.detail;
        const message = typeof detail === 'string' ? detail : JSON.stringify(detail);
        logger.apiError(method, path, response.status, message);
        throw new Error(message || `HTTP ${response.status}`);
    }
    const data = await response.json();
    logger.apiOk(method, path, response.status);
    return data;
}

const PHASE_ROUTES = {
    bidding: 'bid',
    playing: 'play',
    round_end: 'roundend',
    scoreboard: 'scoreboard',
    final: 'final',
};

// Guard: check backend phase matches expected. Redirects if mismatch.
// Returns the game object if phase matches, null if redirected.
export async function guardPhase(gameId, expectedPhase) {
    const game = await request('GET', `/game/${gameId}`);
    if (game.phase !== expectedPhase) {
        const route = PHASE_ROUTES[game.phase] || 'scoreboard';
        logger.resync(gameId, expectedPhase, game.phase);
        window.location.hash = `${route}/${gameId}`;
        return null;
    }
    return game;
}

// Re-sync: fetch game state and navigate to correct screen
export async function resyncGame(gameId) {
    const game = await request('GET', `/game/${gameId}`);
    const route = PHASE_ROUTES[game.phase] || 'scoreboard';
    window.location.hash = `${route}/${gameId}`;
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

export function deletePlayground(name, pin) {
    return request('DELETE', '/playground', { name, pin });
}

export function getPlaygroundStats(shareCode) {
    return request('GET', `/playground/${shareCode}/stats`);
}

export function clearPlaygroundStats(shareCode) {
    return request('DELETE', `/playground/${shareCode}/stats`);
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

export function extendGame(gameId) {
    return request('POST', `/game/${gameId}/extend`);
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
export function undoRound(gameId) {
    return request('POST', `/game/${gameId}/undo`);
}

