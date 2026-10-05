/**
 * Score dialer keypad — 0–9 buffer entry (no tap-commit).
 * Digits call onDigit only; Next is separate (callers own commit).
 * Bottom row: ± · 0 · ⌫ (long-press ⌫ clears). No dedicated Clear key.
 */
import { soundTap, haptic } from './sounds.js';

const LONG_PRESS_MS = 450;

/**
 * @param {{ allowNegatives?: boolean, onDigit: (d: number) => void, onBackspace: () => void, onClear: () => void, onSign?: () => void }} options
 * @returns {HTMLElement}
 */
export function ScoreDialerKeypad({
    allowNegatives = false,
    onDigit,
    onBackspace,
    onClear,
    onSign,
}) {
    const el = document.createElement('div');
    el.className = 'keypad score-dialer-keypad';
    el.setAttribute('data-score-dialer', '1');

    const layout = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
        ['sign', 0, 'back'],
    ];

    layout.forEach((row) => {
        row.forEach((cell) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'keypad-key';
            if (cell === 'sign') {
                btn.id = 'btn-sign';
                btn.setAttribute('data-dialer-sign', '1');
                btn.textContent = '±';
                btn.setAttribute('aria-label', 'Toggle sign');
                if (!allowNegatives || typeof onSign !== 'function') {
                    btn.disabled = true;
                    btn.classList.add('keypad-disabled');
                    btn.setAttribute('aria-disabled', 'true');
                    btn.title = 'Turn on Allow negatives in lobby settings';
                } else {
                    btn.addEventListener('click', () => {
                        haptic();
                        soundTap();
                        onSign();
                    });
                }
            } else if (cell === 'back') {
                btn.setAttribute('data-dialer-backspace', '1');
                btn.textContent = '⌫';
                btn.setAttribute('aria-label', 'Backspace');
                let longPressTimer = null;
                let longPressFired = false;
                const clearTimer = () => {
                    if (longPressTimer != null) {
                        clearTimeout(longPressTimer);
                        longPressTimer = null;
                    }
                };
                btn.addEventListener('pointerdown', () => {
                    longPressFired = false;
                    clearTimer();
                    longPressTimer = setTimeout(() => {
                        longPressFired = true;
                        haptic();
                        soundTap();
                        onClear();
                    }, LONG_PRESS_MS);
                });
                btn.addEventListener('pointerup', () => {
                    clearTimer();
                    if (longPressFired) return;
                    haptic();
                    soundTap();
                    onBackspace();
                });
                btn.addEventListener('pointerleave', clearTimer);
                btn.addEventListener('pointercancel', clearTimer);
            } else {
                btn.textContent = String(cell);
                btn.addEventListener('click', () => {
                    haptic();
                    soundTap();
                    onDigit(cell);
                });
            }
            el.appendChild(btn);
        });
    });

    el.addEventListener('keydown', (event) => {
        if (event.key === 'Delete') {
            event.preventDefault();
            haptic();
            soundTap();
            onClear();
        }
    });
    el.setAttribute('tabindex', '0');
    el.setAttribute('aria-label', 'Score keypad');

    return el;
}
