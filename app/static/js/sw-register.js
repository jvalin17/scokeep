if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js')
        .catch(function(err) { console.warn('SW registration failed', err); });
}
