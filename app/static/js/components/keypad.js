// Phone-style 0-8 keypad component with haptic + sound feedback

// Lazy-init audio context on first tap (browsers require user gesture)
let audioCtx = null;

function playTapSound() {
    try {
        if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.frequency.value = 1200;
        gain.gain.value = 0.08;
        osc.start();
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.06);
        osc.stop(audioCtx.currentTime + 0.06);
    } catch { /* silent fallback */ }
}

function haptic() {
    if (navigator.vibrate) navigator.vibrate(15);
}

export function Keypad({ max = 8, disabled = [], onSelect }) {
    const el = document.createElement('div');
    el.className = 'keypad';

    const keys = [1, 2, 3, 4, 5, 6, 7, 8, 0];

    keys.forEach(num => {
        const btn = document.createElement('button');
        btn.className = 'keypad-key';
        btn.textContent = num;
        btn.type = 'button';

        if (num > max || disabled.includes(num)) {
            btn.classList.add('keypad-disabled');
            btn.disabled = true;
        } else {
            btn.addEventListener('click', () => {
                haptic();
                playTapSound();
                onSelect(num);
            });
        }

        el.appendChild(btn);
    });

    return el;
}
