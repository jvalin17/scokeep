// Phone-style 0-8 keypad component

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
            btn.addEventListener('click', () => onSelect(num));
        }

        el.appendChild(btn);
    });

    return el;
}
