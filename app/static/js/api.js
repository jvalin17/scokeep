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

/**
 * Build relative stats API path (no /api prefix).
 * @param {string} shareCode
 * @param {{ offset?: number, limit?: number, gameType?: string }} [options]
 * @returns {string}
 */
export function buildPlaygroundStatsPath(shareCode, { offset = 0, limit = 40, gameType } = {}) {
    const query = new URLSearchParams();
    if (offset > 0) query.set('offset', String(offset));
    if (offset > 0 || limit !== 40) query.set('limit', String(limit));
    if (gameType) query.set('game_type', gameType);
    const qs = query.toString();
    return `/playground/${shareCode}/stats${qs ? `?${qs}` : ''}`;
}

export function getPlaygroundStats(shareCode, options = {}) {
    return request('GET', buildPlaygroundStatsPath(shareCode, options));
}

export function clearPlaygroundStats(shareCode) {
    return request('DELETE', `/playground/${shareCode}/stats`);
}

// Game — room create / resume / end (server). In-game taps use game-api.js.
export function createGame(playgroundId, players, settings = {}) {
    return request('POST', '/game', {
        playground_id: playgroundId,
        players,
        settings,
    });
}

export function getActiveGame(playgroundId) {
    return request('GET', `/game/active/${playgroundId}`);
}

// Scoreboard (stats screen)
export function getScoreboard(gameId) {
    return request('GET', `/game/${gameId}/scoreboard`);
}
