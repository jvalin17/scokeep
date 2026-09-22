// API client — all fetch() calls to backend

import { logger } from './components/logger.js';
import { NetworkError } from './components/network-error.js';
import { banner } from './components/connection-banner.js';

const BASE = '/api';
const INITIAL_TIMEOUT_MS = 15000;
const RETRY_TIMEOUT_MS = 5000;
const RETRY_DELAYS = [1000, 2000, 4000];

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function jitter(ms) {
    return ms * (0.5 + Math.random() * 0.5);
}

function isRetryable(error) {
    if (error.name === 'AbortError') return true;
    if (error instanceof TypeError && error.message.includes('fetch')) return true;
    return false;
}

async function fetchWithTimeout(method, path, body, timeoutMs) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    const options = {
        method,
        headers: {},
        credentials: 'same-origin',
        signal: controller.signal,
    };
    if (body) {
        options.headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(body);
    }
    try {
        const response = await fetch(`${BASE}${path}`, options);
        clearTimeout(timeoutId);
        return response;
    } catch (error) {
        clearTimeout(timeoutId);
        throw error;
    }
}

async function request(method, path, body = null) {
    logger.apiCall(method, path, body);

    // Layer 0: instant failover if known offline
    if (!navigator.onLine) {
        throw new NetworkError('offline');
    }

    let showedBanner = false;

    for (let attempt = 0; attempt <= RETRY_DELAYS.length; attempt++) {
        try {
            const timeout = attempt === 0 ? INITIAL_TIMEOUT_MS : RETRY_TIMEOUT_MS;
            const response = await fetchWithTimeout(method, path, body, timeout);

            // Check for SW 503 with offline:true body — treat as retryable
            if (response.status === 503) {
                const swBody = await response.json().catch(() => ({}));
                if (swBody.offline) {
                    throw new TypeError('SW offline: Failed to fetch');
                }
                // Regular 503 from server — not retryable
                const detail = swBody.detail || 'Service unavailable';
                logger.apiError(method, path, 503, detail);
                throw new Error(detail);
            }

            // Auth check
            if (response.status === 401 && path !== '/playground/auth' && path !== '/playground') {
                logger.apiError(method, path, 401, 'Session expired');
                window.location.hash = '';
                throw new Error('Session expired — please re-enter your PIN');
            }

            // Other errors — not retryable
            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Request failed' }));
                const detail = error.detail;
                const message = typeof detail === 'string' ? detail : JSON.stringify(detail);
                logger.apiError(method, path, response.status, message);
                throw new Error(message || `HTTP ${response.status}`);
            }

            // Success
            if (showedBanner) banner.hide();
            const data = await response.json();
            logger.apiOk(method, path, response.status);
            return data;
        } catch (error) {
            if (!isRetryable(error)) throw error;
            if (attempt === RETRY_DELAYS.length) break;

            if (attempt === 0) {
                banner.showReconnecting();
                showedBanner = true;
            }
            await sleep(jitter(RETRY_DELAYS[attempt]));
        }
    }

    // All retries exhausted
    logger.apiError(method, path, 0, 'All retries exhausted');
    throw new NetworkError('exhausted');
}

// Exported for tests only
export { request as _request };

const PHASE_ROUTES = {
    bidding: 'bid',
    playing: 'play',
    round_end: 'roundend',
    scoreboard: 'scoreboard',
    review: 'review',
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

export function browsePlaygrounds() {
    return request('GET', '/playground/browse');
}

export function createPlayground(name, pin, players, pinHint = null) {
    const body = { name, pin, players };
    if (pinHint) body.pin_hint = pinHint;
    return request('POST', '/playground', body);
}

export function getPinHint(name) {
    return request('GET', `/playground/hint/${encodeURIComponent(name)}`);
}

export function authPlayground(name, pin) {
    return request('POST', '/playground/auth', { name, pin });
}

export function getPlayground(shareCode) {
    return request('GET', `/playground/${shareCode}`);
}

export function getPlaygroundStats(shareCode, { offset = 0, limit = 40 } = {}) {
    const params = offset > 0 ? `?offset=${offset}&limit=${limit}` : '';
    return request('GET', `/playground/${shareCode}/stats${params}`);
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

export function enterRescore(gameId) {
    return request('POST', `/game/${gameId}/enter-rescore`);
}

// Review phase
export function enterReview(gameId) {
    return request('POST', `/game/${gameId}/enter-review`);
}

export function rescoreRound(gameId, roundNum) {
    return request('POST', `/game/${gameId}/rescore/${roundNum}`);
}

export function confirmFinal(gameId) {
    return request('POST', `/game/${gameId}/confirm-final`);
}

// Scoreboard
export function getScoreboard(gameId) {
    return request('GET', `/game/${gameId}/scoreboard`);
}
export function undoRound(gameId) {
    return request('POST', `/game/${gameId}/undo`);
}
