// Scokeep — client-side router and state manager

import { escapeHtml } from './components/game-utils.js';
import { logger } from './components/logger.js';
import { isLocalGame } from './resolve-api.js';
import { homeScreen } from './screens/home.js';
import { lobbyScreen } from './screens/lobby.js';
import { biddingScreen } from './screens/bidding.js';
import { playScreen } from './screens/play.js';
import { roundendScreen } from './screens/roundend.js';
import { scoreboardScreen } from './screens/scoreboard.js';
import { reviewScreen } from './screens/review.js';
import { finalScreen } from './screens/final.js';
import { statsScreen } from './screens/stats.js';


const state = {
    playground: null,
    game: null,
    currentEntry: null,
};

const appElement = document.getElementById('app');
let currentScreen = null;

// Keep-alive: ping /api/health every 10 min on game screens to prevent Render spin-down
const KEEP_ALIVE_INTERVAL_MS = 10 * 60 * 1000;
const GAME_SCREENS = new Set(['bid', 'play', 'roundend', 'scoreboard', 'review']);
let keepAliveTimer = null;

function startKeepAlive() {
    if (keepAliveTimer) return;
    keepAliveTimer = setInterval(() => {
        const controller = new AbortController();
        setTimeout(() => controller.abort(), 10000);
        fetch('/api/health', { credentials: 'same-origin', signal: controller.signal }).catch(() => {});
    }, KEEP_ALIVE_INTERVAL_MS);
}

function stopKeepAlive() {
    if (keepAliveTimer) {
        clearInterval(keepAliveTimer);
        keepAliveTimer = null;
    }
}

const routes = {
    '': homeScreen,
    'playground': lobbyScreen,
    'bid': biddingScreen,
    'play': playScreen,
    'roundend': roundendScreen,
    'scoreboard': scoreboardScreen,
    'review': reviewScreen,
    'final': finalScreen,
    'stats': statsScreen,

};

function parseHash() {
    const hash = window.location.hash.slice(1) || '';
    const parts = hash.split('/').filter(Boolean);
    return {
        screen: parts[0] || '',
        params: parts.slice(1),
    };
}

function navigate(path) {
    window.location.hash = path;
}

async function render() {
    const { screen, params } = parseHash();
    const screenModule = routes[screen] || routes[''];

    logger.navigate(screen, params);

    if (GAME_SCREENS.has(screen)) {
        startKeepAlive();
    } else {
        stopKeepAlive();
    }

    if (currentScreen && currentScreen.unmount) {
        currentScreen.unmount();
    }

    currentScreen = screenModule;
    appElement.innerHTML = '';

    try {
        await screenModule.mount(appElement, state, { navigate, params });
    } catch (error) {
        logger.error('screen', `error on ${screen}: ${error.message}`);
        // Try to resync if we have a game ID
        const gameId = params[0];
        // Only attempt server resync for non-local game IDs
        const isLocalId = isLocalGame(gameId);
        if (gameId && !isLocalId && screen !== '' && screen !== 'playground' && screen !== 'stats') {
            try {
                logger.warn('resync', `attempting resync for game ${gameId}`);
                const resp = await fetch(`/api/game/${gameId}`, { credentials: 'same-origin' });
                if (resp.ok) {
                    const game = await resp.json();
                    const routeMap = { bidding: 'bid', playing: 'play', round_end: 'roundend', scoreboard: 'scoreboard', review: 'review', final: 'final' };
                    logger.resync(gameId, screen, routeMap[game.phase] || 'scoreboard');
                    const target = routeMap[game.phase] || 'scoreboard';
                    if (target !== screen) {
                        navigate(`${target}/${gameId}`);
                        return;
                    }
                }
            } catch (resyncErr) {
                logger.error('resync', `resync failed: ${resyncErr.message}`);
            }
        }
        appElement.innerHTML = `
            <div class="error-screen">
                <h2>Something went wrong</h2>
                <p>${escapeHtml(error.message)}</p>
                <button id="err-home" class="btn">Go Home</button>
                <button id="err-reload" class="btn" style="margin-top:8px;">Reload</button>
            </div>
        `;
        appElement.querySelector('#err-home').addEventListener('click', () => { location.hash = ''; });
        appElement.querySelector('#err-reload').addEventListener('click', () => { location.reload(); });
    }
}

window.addEventListener('hashchange', render);
render();

// Export for screens to use
window.scokeep = { state, navigate };
