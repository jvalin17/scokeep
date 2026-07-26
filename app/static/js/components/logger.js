// Observability logger — structured logs with levels, context, and history

const MAX_HISTORY = 200;
const history = [];

function timestamp() {
    return new Date().toISOString().slice(11, 23);
}

function log(level, category, message, data = null) {
    const entry = { ts: timestamp(), level, cat: category, msg: message };
    if (data) entry.data = data;
    history.push(entry);
    if (history.length > MAX_HISTORY) history.shift();

    const prefix = `[${entry.ts}] [${category}]`;
    if (level === 'error') {
        console.error(prefix, message, data || '');
    } else if (level === 'warn') {
        console.warn(prefix, message, data || '');
    } else {
        console.log(prefix, message, data || '');
    }
}

export const logger = {
    // API calls
    apiCall(method, path, body) {
        log('info', 'api', `${method} ${path}`, body || undefined);
    },
    apiOk(method, path, status) {
        log('info', 'api', `${method} ${path} → ${status}`);
    },
    apiError(method, path, status, detail) {
        log('error', 'api', `${method} ${path} → ${status}: ${detail}`);
    },

    // Navigation
    navigate(screen, params) {
        log('info', 'nav', `→ ${screen || 'home'}`, params.length ? params : undefined);
    },

    // Game state
    phase(gameId, phase) {
        log('info', 'game', `game ${gameId} phase: ${phase}`);
    },
    action(name, detail) {
        log('info', 'action', name, detail || undefined);
    },

    // Errors and recovery
    error(category, message, data) {
        log('error', category, message, data || undefined);
    },
    warn(category, message, data) {
        log('warn', category, message, data || undefined);
    },
    resync(gameId, fromPhase, toPhase) {
        log('warn', 'resync', `game ${gameId}: ${fromPhase} → ${toPhase}`);
    },

    // Sound
    sound(name) {
        log('info', 'sound', name);
    },

    // Dump full history (for debugging)
    dump() {
        console.table(history);
        return history;
    },

    // Get recent entries
    recent(n = 20) {
        return history.slice(-n);
    },
};

// Expose globally for debugging in console
window.__scokeepLogs = logger;
