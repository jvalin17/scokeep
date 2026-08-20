// Confirm modal — replaces browser confirm() with styled dialog

export function confirmModal(title, message, confirmText = 'Confirm', danger = false) {
    return new Promise(resolve => {
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.innerHTML = `
            <div class="modal-box">
                <h3>${title}</h3>
                <p>${message}</p>
                <div class="modal-actions">
                    <button class="btn" id="modal-cancel">Cancel</button>
                    <button class="btn ${danger ? 'btn-danger' : 'btn-primary'}" id="modal-confirm">${confirmText}</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);

        const close = (result) => {
            overlay.remove();
            resolve(result);
        };

        overlay.querySelector('#modal-cancel').addEventListener('click', () => close(false));
        overlay.querySelector('#modal-confirm').addEventListener('click', () => close(true));
        overlay.addEventListener('click', (e) => { if (e.target === overlay) close(false); });
    });
}

/**
 * Type-to-confirm modal — user must type an exact phrase to proceed.
 * Returns true only if user typed the phrase and clicked confirm.
 */
export function typeConfirmModal(title, message, phrase, confirmText = 'Confirm', variant = 'warning') {
    return new Promise(resolve => {
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        const variantClass = variant === 'danger' ? 'modal-danger' : 'modal-warning';
        overlay.innerHTML = `
            <div class="modal-box ${variantClass}">
                <h3>${title}</h3>
                <p>${message}</p>
                <p style="font-size:0.8rem;color:var(--text-muted);margin-bottom:8px;">Type <strong>${phrase}</strong> to confirm</p>
                <input type="text" id="modal-input" placeholder="${phrase}" autocomplete="off"
                    style="width:100%;padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius-sm);font-size:0.9rem;margin-bottom:16px;text-align:center;" />
                <div class="modal-actions">
                    <button class="btn" id="modal-cancel">Cancel</button>
                    <button class="btn btn-danger" id="modal-confirm" disabled>${confirmText}</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);

        const input = overlay.querySelector('#modal-input');
        const btn = overlay.querySelector('#modal-confirm');

        input.addEventListener('input', () => {
            const match = input.value.trim().toLowerCase() === phrase.toLowerCase();
            btn.disabled = !match;
        });

        const close = (result) => {
            overlay.remove();
            resolve(result);
        };

        btn.addEventListener('click', () => close(true));
        overlay.querySelector('#modal-cancel').addEventListener('click', () => close(false));
        overlay.addEventListener('click', (e) => { if (e.target === overlay) close(false); });
        input.focus();
    });
}
