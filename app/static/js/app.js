// Scokeep — client-side router and state manager

import { homeScreen } from './screens/home.js';
import { lobbyScreen } from './screens/lobby.js';
import { biddingScreen } from './screens/bidding.js';
import { playScreen } from './screens/play.js';
import { roundendScreen } from './screens/roundend.js';
import { scoreboardScreen } from './screens/scoreboard.js';
import { finalScreen } from './screens/final.js';
import { statsScreen } from './screens/stats.js';
import { freescoreScreen } from './screens/freescore.js';

const state = {
    playground: null,
    game: null,
    currentEntry: null,
};

const appElement = document.getElementById('app');
let currentScreen = null;

const routes = {
    '': homeScreen,
    'playground': lobbyScreen,
    'bid': biddingScreen,
    'play': playScreen,
    'roundend': roundendScreen,
    'scoreboard': scoreboardScreen,
    'final': finalScreen,
    'stats': statsScreen,
    'freescore': freescoreScreen,
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

    console.log(`[scokeep] navigate → ${screen || 'home'}`, params.length ? params : '');

    if (currentScreen && currentScreen.unmount) {
        currentScreen.unmount();
    }

    currentScreen = screenModule;
    appElement.innerHTML = '';

    try {
        await screenModule.mount(appElement, state, { navigate, params });
    } catch (error) {
        console.error(`[scokeep] screen error on ${screen}:`, error.message);
        // Try to resync if we have a game ID
        const gameId = params[0];
        if (gameId && screen !== '' && screen !== 'playground' && screen !== 'stats') {
            try {
                console.log(`[scokeep] attempting resync for game ${gameId}`);
                const resp = await fetch(`/api/game/${gameId}`, { credentials: 'same-origin' });
                if (resp.ok) {
                    const game = await resp.json();
                    console.log(`[scokeep] game phase: ${game.phase}, redirecting`);
                    const routeMap = { bidding: 'bid', playing: 'play', round_end: 'roundend', scoreboard: 'scoreboard', final: 'final' };
                    const target = routeMap[game.phase] || 'scoreboard';
                    if (target !== screen) {
                        navigate(`${target}/${gameId}`);
                        return;
                    }
                }
            } catch (resyncErr) {
                console.error(`[scokeep] resync failed:`, resyncErr.message);
            }
        }
        appElement.innerHTML = `
            <div class="error-screen">
                <h2>Something went wrong</h2>
                <p>${error.message}</p>
                <button onclick="location.hash=''" class="btn">Go Home</button>
                <button onclick="location.reload()" class="btn" style="margin-top:8px;">Reload</button>
            </div>
        `;
    }
}

window.addEventListener('hashchange', render);
render();

// Export for screens to use
window.scokeep = { state, navigate };
