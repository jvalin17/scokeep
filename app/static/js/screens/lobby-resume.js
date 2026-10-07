/**
 * Resume Game visibility — only for the tab matching the active game type.
 */

/**
 * @param {{ settings?: { game_type?: string } } | null | undefined} activeGame
 * @param {string} selectedGameType
 * @returns {boolean}
 */
export function shouldShowResumeForTab(activeGame, selectedGameType) {
    if (!activeGame) return false;
    const activeType = activeGame.settings?.game_type || 'kachuful';
    const tab = selectedGameType || 'kachuful';
    return activeType === tab;
}

/**
 * Prefer selecting the tab that owns the in-progress game.
 * @param {{ settings?: { game_type?: string } } | null | undefined} activeGame
 * @param {string} fallback
 * @returns {string}
 */
export function initialGameTypeForLobby(activeGame, fallback = 'kachuful') {
    if (!activeGame) return fallback || 'kachuful';
    return activeGame.settings?.game_type || fallback || 'kachuful';
}

/**
 * @param {{ current_round?: number, settings?: { game_type?: string } } | null | undefined} activeGame
 * @param {string} selectedGameType
 * @returns {string} HTML
 */
export function renderResumeBlock(activeGame, selectedGameType) {
    if (!shouldShowResumeForTab(activeGame, selectedGameType)) return '';
    const round = activeGame.current_round ?? 1;
    return `
                        <div class="active-game-actions">
                            <button id="resume-game" class="btn btn-primary btn-large">Resume Game (Round ${round})</button>
                            <button id="game-settings-toggle" class="btn-text" style="font-size:0.8rem;margin-top:8px;">⚙ Options</button>
                            <div id="game-settings-panel" class="hidden" style="margin-top:8px;">
                                <button id="end-active-game" class="btn-small" style="background:var(--danger);color:#fff;font-size:0.8rem;">End Game</button>
                            </div>
                        </div>
                    `;
}
