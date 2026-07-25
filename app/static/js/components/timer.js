// Configurable countdown timer with cancel

export function Timer({ seconds, onExpire, onCancel }) {
    const el = document.createElement('div');
    el.className = 'timer';

    let remaining = seconds;
    let intervalId = null;

    function render() {
        el.innerHTML = `
            <button type="button" class="btn btn-small timer-next">Next</button>
            <div class="timer-display">${remaining}s</div>
            <button type="button" class="btn btn-small timer-cancel">Change</button>
        `;
        el.querySelector('.timer-next').addEventListener('click', () => {
            stop();
            if (onExpire) onExpire();
        });
        el.querySelector('.timer-cancel').addEventListener('click', () => {
            stop();
            if (onCancel) onCancel();
        });
    }

    function start() {
        render();
        intervalId = setInterval(() => {
            remaining--;
            if (remaining <= 0) {
                stop();
                if (onExpire) onExpire();
            } else {
                const display = el.querySelector('.timer-display');
                if (display) display.textContent = `${remaining}s`;
            }
        }, 1000);
    }

    function stop() {
        if (intervalId) {
            clearInterval(intervalId);
            intervalId = null;
        }
    }

    start();

    el.destroy = stop;
    return el;
}
