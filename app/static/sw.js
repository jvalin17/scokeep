// Service worker — cache app shell for offline use

const CACHE_NAME = 'scokeep-v25';
const APP_SHELL = [
    '/',
    '/static/css/style.css',
    '/static/js/app.js',
    '/static/js/api.js',
    '/static/js/screens/home.js',
    '/static/js/screens/lobby.js',
    '/static/js/screens/bidding.js',
    '/static/js/screens/play.js',
    '/static/js/screens/roundend.js',
    '/static/js/screens/scoreboard.js',
    '/static/js/screens/final.js',
    '/static/js/screens/stats.js',
    '/static/js/components/keypad.js',
    '/static/js/components/sounds.js',
    '/static/js/components/logger.js',
    '/static/js/components/game-utils.js',
    '/static/js/components/drag-reorder.js',
    '/static/js/components/timer.js',
    '/static/js/components/entry-utils.js',
    '/static/js/components/screen-parts.js',
    '/static/manifest.json',
    '/static/icons/icon-192.png',
    '/static/icons/icon-512.png',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(APP_SHELL))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        ).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // API calls: network only (need fresh data)
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(fetch(event.request));
        return;
    }

    // App shell: cache first, fallback to network
    event.respondWith(
        caches.match(event.request).then(cached => {
            const fetchPromise = fetch(event.request).then(response => {
                if (response.ok) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                }
                return response;
            }).catch(() => cached);

            return cached || fetchPromise;
        })
    );
});
