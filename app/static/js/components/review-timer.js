// Review timer overlay — shows selected value large with countdown
// Used by bidding and roundend screens for the configurable review window

import { haptic } from './sounds.js';

/**
 * Show a review overlay with the selected value and a countdown timer.
 * @param {HTMLElement} container - Parent element to append the overlay to
 * @param {number} value - The selected bid/hand value
 * @param {number} durationMs - Timer duration in ms (0 = skip review)
 * @param {function} onConfirm - Called when timer expires or user confirms
 * @param {function} onChange - Called when user taps "Change" to re-enter
 */
export function showReviewTimer(container, value, durationMs, onConfirm, onChange) {
    if (durationMs <= 0) {
        onConfirm(value);
        return null;
    }

    const overlay = document.createElement('div');
    overlay.className = 'review-overlay';

    const seconds = Math.ceil(durationMs / 1000);
    let remaining = seconds;
    let timerId = null;

    function renderTimer() {
        overlay.innerHTML = `
            <div class="review-value">${value}</div>
            <div class="review-countdown">${remaining}s</div>
            <div class="review-actions">
                <button class="btn review-confirm">Confirm</button>
                <button class="btn-text review-change">Change</button>
            </div>
        `;

        overlay.querySelector('.review-confirm').addEventListener('click', () => {
            haptic();
            clearInterval(timerId);
            overlay.remove();
            onConfirm(value);
        });

        overlay.querySelector('.review-change').addEventListener('click', () => {
            haptic();
            clearInterval(timerId);
            overlay.remove();
            onChange();
        });
    }

    renderTimer();
    container.appendChild(overlay);

    timerId = setInterval(() => {
        remaining--;
        const countdownEl = overlay.querySelector('.review-countdown');
        if (countdownEl) countdownEl.textContent = `${remaining}s`;
        if (remaining <= 0) {
            clearInterval(timerId);
            overlay.remove();
            onConfirm(value);
        }
    }, 1000);

    return { cancel: () => { clearInterval(timerId); overlay.remove(); } };
}
