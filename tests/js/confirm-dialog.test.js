import { describe, it, expect, vi, beforeEach } from 'vitest';
import { showConfirmDialog, showPromptDialog } from '../../app/static/js/components/confirm-dialog.js';

describe('showConfirmDialog', () => {
    beforeEach(() => {
        document.body.innerHTML = '';
    });

    it('renders an inline dialog overlay', async () => {
        const promise = showConfirmDialog('End this game?');
        const overlay = document.querySelector('.confirm-overlay');
        expect(overlay).not.toBeNull();
        expect(overlay.textContent).toContain('End this game?');

        // Click cancel to resolve
        overlay.querySelector('.confirm-cancel').click();
        const result = await promise;
        expect(result).toBe(false);
    });

    it('resolves true when confirm is clicked', async () => {
        const promise = showConfirmDialog('Are you sure?');
        const overlay = document.querySelector('.confirm-overlay');
        overlay.querySelector('.confirm-ok').click();
        const result = await promise;
        expect(result).toBe(true);
    });

    it('removes dialog from DOM after resolution', async () => {
        const promise = showConfirmDialog('Test');
        document.querySelector('.confirm-ok').click();
        await promise;
        expect(document.querySelector('.confirm-overlay')).toBeNull();
    });

    it('does not use native confirm()', () => {
        const spy = vi.spyOn(window, 'confirm');
        showConfirmDialog('Test');
        expect(spy).not.toHaveBeenCalled();
        document.querySelector('.confirm-cancel').click();
        spy.mockRestore();
    });
});

describe('showPromptDialog', () => {
    beforeEach(() => {
        document.body.innerHTML = '';
    });

    it('renders an inline prompt dialog with input field', async () => {
        const promise = showPromptDialog('Edit score:', '42');
        const overlay = document.querySelector('.confirm-overlay');
        expect(overlay).not.toBeNull();
        expect(overlay.textContent).toContain('Edit score:');
        const input = overlay.querySelector('.prompt-input');
        expect(input).not.toBeNull();
        expect(input.value).toBe('42');

        overlay.querySelector('.confirm-cancel').click();
        const result = await promise;
        expect(result).toBeNull();
    });

    it('resolves with input value on confirm', async () => {
        const promise = showPromptDialog('Enter value:', '10');
        const overlay = document.querySelector('.confirm-overlay');
        const input = overlay.querySelector('.prompt-input');
        input.value = '25';
        overlay.querySelector('.confirm-ok').click();
        const result = await promise;
        expect(result).toBe('25');
    });

    it('resolves null on cancel', async () => {
        const promise = showPromptDialog('Enter value:', '10');
        document.querySelector('.confirm-cancel').click();
        const result = await promise;
        expect(result).toBeNull();
    });

    it('does not use native prompt()', () => {
        const spy = vi.spyOn(window, 'prompt');
        showPromptDialog('Test', '');
        expect(spy).not.toHaveBeenCalled();
        document.querySelector('.confirm-cancel').click();
        spy.mockRestore();
    });

    it('removes dialog from DOM after resolution', async () => {
        const promise = showPromptDialog('Test', '');
        document.querySelector('.confirm-ok').click();
        await promise;
        expect(document.querySelector('.confirm-overlay')).toBeNull();
    });
});
