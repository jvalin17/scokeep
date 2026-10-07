/**
 * Score dialer keypad layout — bottom row ± · 0 · ⌫
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../../app/static/js/components/sounds.js', () => ({
  soundTap: vi.fn(),
  haptic: vi.fn(),
  isMuted: () => true,
}));

import { ScoreDialerKeypad } from '../../app/static/js/components/score-dialer-keypad.js';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('ScoreDialerKeypad', () => {
  it('lays out four rows with bottom ± 0 backspace', () => {
    const keypad = ScoreDialerKeypad({
      allowNegatives: true,
      onDigit: vi.fn(),
      onBackspace: vi.fn(),
      onClear: vi.fn(),
      onSign: vi.fn(),
    });
    const labels = Array.from(keypad.querySelectorAll('button')).map((btn) =>
      btn.textContent.trim(),
    );
    expect(labels).toEqual(['1', '2', '3', '4', '5', '6', '7', '8', '9', '±', '0', '⌫']);
    expect(labels).not.toContain('C');
    expect(keypad.querySelector('#btn-clear')).toBeNull();
  });

  it('greys out ± when negatives are not allowed', () => {
    const onSign = vi.fn();
    const keypad = ScoreDialerKeypad({
      allowNegatives: false,
      onDigit: vi.fn(),
      onBackspace: vi.fn(),
      onClear: vi.fn(),
      onSign,
    });
    const signBtn = keypad.querySelector('#btn-sign');
    expect(signBtn.disabled).toBe(true);
    expect(signBtn.classList.contains('keypad-disabled')).toBe(true);
    signBtn.click();
    expect(onSign).not.toHaveBeenCalled();
  });

  it('calls onSign when ± is enabled', () => {
    const onSign = vi.fn();
    const keypad = ScoreDialerKeypad({
      allowNegatives: true,
      onDigit: vi.fn(),
      onBackspace: vi.fn(),
      onClear: vi.fn(),
      onSign,
    });
    const signBtn = keypad.querySelector('#btn-sign');
    expect(signBtn.classList.contains('keypad-disabled')).toBe(false);
    signBtn.click();
    expect(onSign).toHaveBeenCalledTimes(1);
  });

  it('clears on Delete key', () => {
    const onClear = vi.fn();
    const keypad = ScoreDialerKeypad({
      allowNegatives: false,
      onDigit: vi.fn(),
      onBackspace: vi.fn(),
      onClear,
      onSign: vi.fn(),
    });
    keypad.dispatchEvent(new KeyboardEvent('keydown', { key: 'Delete', bubbles: true }));
    expect(onClear).toHaveBeenCalledTimes(1);
  });
});
