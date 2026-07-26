// Sound effects — synthesized tones, no audio files needed

export function isMuted() { return localStorage.getItem('scokeep_mute') === '1'; }
export function toggleMute() {
    const muted = !isMuted();
    localStorage.setItem('scokeep_mute', muted ? '1' : '0');
    return muted;
}

let ctx = null;

function getCtx() {
    if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
    if (ctx.state === 'suspended') ctx.resume();
    return ctx;
}

function tone(freq, duration = 0.08, vol = 0.07) {
    if (isMuted()) return;
    try {
        const c = getCtx();
        const osc = c.createOscillator();
        const gain = c.createGain();
        osc.connect(gain);
        gain.connect(c.destination);
        osc.frequency.value = freq;
        gain.gain.value = vol;
        osc.start();
        gain.gain.exponentialRampToValueAtTime(0.001, c.currentTime + duration);
        osc.stop(c.currentTime + duration);
    } catch { /* silent */ }
}

function chord(freqs, duration = 0.15, vol = 0.05) {
    freqs.forEach(f => tone(f, duration, vol));
}

// Keypad tap — short click
export function soundTap() { tone(1200, 0.06, 0.08); }

// Next round — ascending double beep
export function soundNextRound() {
    tone(600, 0.1); setTimeout(() => tone(900, 0.12), 120);
}

// Start round — bright chord
export function soundStartRound() { chord([523, 659, 784], 0.2); }

// Score round — warm resolved chord
export function soundScoreRound() { chord([440, 554, 659], 0.25, 0.06); }

// End game — descending fanfare
export function soundEndGame() {
    tone(784, 0.15); setTimeout(() => tone(659, 0.15), 150);
    setTimeout(() => tone(523, 0.25), 300);
}

// Undo — low descending tone
export function soundUndo() { tone(400, 0.12); setTimeout(() => tone(300, 0.15), 130); }

// Haptic vibration
export function haptic(ms = 15) { if (navigator.vibrate) navigator.vibrate(ms); }
