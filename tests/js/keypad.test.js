import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Keypad, InlineKeypad } from '../../app/static/js/components/keypad.js';

// Stub sounds module — Keypad imports haptic/soundTap
vi.mock('../../app/static/js/components/sounds.js', () => ({
    soundTap: vi.fn(),
    haptic: vi.fn(),
}));

beforeEach(() => {
    document.body.innerHTML = '';
});

describe('Keypad', () => {
    it('renders phone-style grid when max <= 8', () => {
        const el = Keypad({ max: 8, onSelect: vi.fn() });
        document.body.appendChild(el);
        const keys = el.querySelectorAll('.keypad-key');
        expect(keys.length).toBe(9); // 1-8 + 0
        expect(el.classList.contains('keypad')).toBe(true);
    });

    it('renders all values up to max when max > 8', () => {
        const onSelect = vi.fn();
        const el = Keypad({ max: 13, onSelect });
        document.body.appendChild(el);
        // Should have buttons 0 through 13 = 14 buttons
        const keys = el.querySelectorAll('button');
        expect(keys.length).toBe(14);
        // Button for 13 should exist and be clickable
        const btn13 = Array.from(keys).find(b => b.textContent === '13');
        expect(btn13).not.toBeUndefined();
        expect(btn13.disabled).toBe(false);
    });

    it('fires onSelect with correct value for keys > 8', () => {
        const onSelect = vi.fn();
        const el = Keypad({ max: 10, onSelect });
        document.body.appendChild(el);
        const keys = el.querySelectorAll('button');
        const btn10 = Array.from(keys).find(b => b.textContent === '10');
        expect(btn10).not.toBeUndefined();
        btn10.click();
        expect(onSelect).toHaveBeenCalledWith(10);
    });

    it('disables keys beyond max when max > 8', () => {
        const el = Keypad({ max: 10, disabled: [5], onSelect: vi.fn() });
        document.body.appendChild(el);
        const keys = el.querySelectorAll('button');
        const btn5 = Array.from(keys).find(b => b.textContent === '5');
        expect(btn5.disabled).toBe(true);
    });

    it('uses inline layout when useInline is true even if max <= 8', () => {
        const el = Keypad({ max: 5, useInline: true, onSelect: vi.fn() });
        document.body.appendChild(el);
        // Should use inline-keypad class, not phone grid keypad class
        expect(el.classList.contains('inline-keypad')).toBe(true);
        expect(el.classList.contains('keypad')).toBe(false);
        // Should have buttons 0-5 = 6 buttons
        const keys = el.querySelectorAll('button');
        expect(keys.length).toBe(6);
    });
});

describe('InlineKeypad', () => {
    it('renders buttons 0 to max', () => {
        const el = InlineKeypad({ max: 13, onSelect: vi.fn() });
        document.body.appendChild(el);
        const keys = el.querySelectorAll('.inline-keypad-key');
        expect(keys.length).toBe(14);
    });

    it('adds keypad-selected class on click', () => {
        const el = InlineKeypad({ max: 5, onSelect: vi.fn() });
        document.body.appendChild(el);
        const btn3 = Array.from(el.querySelectorAll('button')).find(b => b.textContent === '3');
        btn3.click();
        expect(btn3.classList.contains('keypad-selected')).toBe(true);
    });

    it('removes previous keypad-selected on new click', () => {
        const el = InlineKeypad({ max: 5, onSelect: vi.fn() });
        document.body.appendChild(el);
        const buttons = el.querySelectorAll('button');
        const btn2 = Array.from(buttons).find(b => b.textContent === '2');
        const btn4 = Array.from(buttons).find(b => b.textContent === '4');
        btn2.click();
        btn4.click();
        expect(btn2.classList.contains('keypad-selected')).toBe(false);
        expect(btn4.classList.contains('keypad-selected')).toBe(true);
    });
});
