// Scokeep — client-side router and state manager

import { homeScreen } from './screens/home.js';
import { lobbyScreen } from './screens/lobby.js';
import { biddingScreen } from './screens/bidding.js';
import { playScreen } from './screens/play.js';
import { roundendScreen } from './screens/roundend.js';
import { scoreboardScreen } from './screens/scoreboard.js';
import { finalScreen } from './screens/final.js';

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

    if (currentScreen && currentScreen.unmount) {
        currentScreen.unmount();
    }

    currentScreen = screenModule;
    appElement.innerHTML = '';

    try {
        await screenModule.mount(appElement, state, { navigate, params });
    } catch (error) {
        appElement.innerHTML = `
            <div class="error-screen">
                <h2>Something went wrong</h2>
                <p>${error.message}</p>
                <button onclick="location.hash=''" class="btn">Go Home</button>
            </div>
        `;
    }
}

window.addEventListener('hashchange', render);
render();

// Export for screens to use
window.scokeep = { state, navigate };
