/**
 * Inline confirmation dialog — PWA-safe replacement for window.confirm().
 *
 * Usage:
 *   const confirmed = await showConfirmDialog('End this game?');
 *   if (confirmed) { ... }
 */

/**
 * Show an inline confirmation dialog and return a Promise<boolean>.
 * Resolves true on confirm, false on cancel. Dialog is removed from DOM after.
 */
/**
 * Show an inline prompt dialog with an input field. PWA-safe replacement for window.prompt().
 * Resolves with the input value on confirm, or null on cancel.
 */
export function showPromptDialog(message, defaultValue = '') {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.className = 'confirm-overlay';
        overlay.innerHTML = `
            <div class="action-dialog">
                <p class="confirm-message">${message}</p>
                <input class="prompt-input" type="text" value="${defaultValue}" />
                <div class="confirm-actions">
                    <button class="action-btn confirm-cancel">Cancel</button>
                    <button class="action-btn action-btn-danger confirm-ok">OK</button>
                </div>
            </div>
        `;

        const input = overlay.querySelector('.prompt-input');

        function cleanup(result) {
            overlay.remove();
            resolve(result);
        }

        overlay.querySelector('.confirm-cancel').addEventListener('click', () => cleanup(null));
        overlay.querySelector('.confirm-ok').addEventListener('click', () => cleanup(input.value));
        overlay.addEventListener('click', (event) => {
            if (event.target === overlay) cleanup(null);
        });

        document.body.appendChild(overlay);
        input.focus();
        input.select();
    });
}

export function showConfirmDialog(message) {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.className = 'confirm-overlay';
        overlay.innerHTML = `
            <div class="action-dialog">
                <p class="confirm-message">${message}</p>
                <div class="confirm-actions">
                    <button class="action-btn confirm-cancel">Cancel</button>
                    <button class="action-btn action-btn-danger confirm-ok">Confirm</button>
                </div>
            </div>
        `;

        function cleanup(result) {
            overlay.remove();
            resolve(result);
        }

        overlay.querySelector('.confirm-cancel').addEventListener('click', () => cleanup(false));
        overlay.querySelector('.confirm-ok').addEventListener('click', () => cleanup(true));
        overlay.addEventListener('click', (event) => {
            if (event.target === overlay) cleanup(false);
        });

        document.body.appendChild(overlay);
    });
}
