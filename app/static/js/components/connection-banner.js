/**
 * Connection status banner — fixed-position bar at top of screen.
 * Shows reconnecting, offline, synced, or sync-failed states.
 */

const BANNER_ID = 'connection-banner';

function getOrCreate() {
  let el = document.getElementById(BANNER_ID);
  if (el) return el;
  el = document.createElement('div');
  el.id = BANNER_ID;
  Object.assign(el.style, {
    position: 'fixed',
    top: '0',
    left: '0',
    width: '100%',
    padding: '8px 16px',
    textAlign: 'center',
    fontWeight: '600',
    fontSize: '14px',
    color: '#fff',
    zIndex: '9999',
    boxSizing: 'border-box',
  });
  document.body.prepend(el);
  return el;
}

let autoHideTimer = null;

export const banner = {
  showReconnecting() {
    const el = getOrCreate();
    el.style.backgroundColor = '#f59e0b';
    el.textContent = 'Reconnecting\u2026';
    el.onclick = null;
    el.style.cursor = 'default';
    clearAutoHide();
  },

  showOffline() {
    const el = getOrCreate();
    el.style.backgroundColor = '#ea580c';
    el.textContent = 'Playing offline \u2014 will sync when back online';
    el.onclick = null;
    el.style.cursor = 'default';
    clearAutoHide();
  },

  showSynced() {
    const el = getOrCreate();
    el.style.backgroundColor = '#16a34a';
    el.textContent = 'Synced \u2713';
    el.onclick = null;
    el.style.cursor = 'default';
    clearAutoHide();
    autoHideTimer = setTimeout(() => banner.hide(), 3000);
  },

  showSyncFailed(onRetry) {
    const el = getOrCreate();
    el.style.backgroundColor = '#dc2626';
    el.textContent = 'Sync failed \u2014 tap to retry';
    el.style.cursor = 'pointer';
    el.onclick = onRetry || null;
    clearAutoHide();
  },

  hide() {
    clearAutoHide();
    const el = document.getElementById(BANNER_ID);
    if (el) el.remove();
  },
};

function clearAutoHide() {
  if (autoHideTimer) {
    clearTimeout(autoHideTimer);
    autoHideTimer = null;
  }
}
