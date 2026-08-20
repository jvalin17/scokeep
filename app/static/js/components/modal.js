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
