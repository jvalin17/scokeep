// Registers the content-hashed service worker. No manual version to maintain:
// /sw.js embeds CACHE_NAME from a hash of the app shell; we pass that as ?v=
// so CDNs cannot keep serving a stale worker script under a bare URL.
(async function registerServiceWorker() {
    if (!('serviceWorker' in navigator)) return;
    try {
        const response = await fetch('/sw.js', { cache: 'no-store' });
        if (!response.ok) throw new Error('sw.js HTTP ' + response.status);
        const source = await response.text();
        const match = source.match(/CACHE_NAME\s*=\s*['"]([^'"]+)['"]/);
        const version = match ? match[1] : String(Date.now());
        await navigator.serviceWorker.register(
            '/sw.js?v=' + encodeURIComponent(version)
        );
    } catch (err) {
        console.warn('SW registration failed', err);
    }
})();
