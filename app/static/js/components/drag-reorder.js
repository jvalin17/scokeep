/**
 * Touch drag-to-reorder for player lists.
 * Extracted from lobby.js to reduce file size and enable reuse.
 */

export function initDragReorder(container, playerList, players, onReorder) {
    let dragEl = null;
    let dragIndex = null;
    let startY = 0;
    let currentY = 0;

    container.querySelectorAll('.drag-handle').forEach(handle => {
        handle.addEventListener('touchstart', (e) => {
            e.preventDefault();
            dragIndex = parseInt(handle.dataset.drag);
            dragEl = handle.closest('.lobby-player');
            startY = e.touches[0].clientY;
            currentY = startY;
            dragEl.classList.add('dragging');
        }, { passive: false });
    });

    const onTouchMove = (e) => {
        if (dragEl === null) return;
        e.preventDefault();
        currentY = e.touches[0].clientY;
        dragEl.style.transform = `translateY(${currentY - startY}px)`;

        const items = [...playerList.querySelectorAll('.lobby-player')];
        for (const item of items) {
            if (item === dragEl) continue;
            const rect = item.getBoundingClientRect();
            const mid = rect.top + rect.height / 2;
            if (currentY < mid && parseInt(item.dataset.index) < dragIndex) {
                item.style.transform = 'translateY(48px)';
            } else if (currentY > mid && parseInt(item.dataset.index) > dragIndex) {
                item.style.transform = 'translateY(-48px)';
            } else {
                item.style.transform = '';
            }
        }
    };

    const onTouchEnd = () => {
        if (dragEl === null) return;
        const items = [...playerList.querySelectorAll('.lobby-player')];
        let dropIndex = dragIndex;
        for (const item of items) {
            if (item === dragEl) continue;
            const rect = item.getBoundingClientRect();
            const mid = rect.top + rect.height / 2;
            const idx = parseInt(item.dataset.index);
            if (currentY < mid && idx < dragIndex) {
                dropIndex = Math.min(dropIndex, idx);
            } else if (currentY > mid && idx > dragIndex) {
                dropIndex = Math.max(dropIndex, idx);
            }
        }
        if (dropIndex !== dragIndex) {
            const moved = players.splice(dragIndex, 1)[0];
            players.splice(dropIndex, 0, moved);
        }
        dragEl = null;
        dragIndex = null;
        onReorder();
    };

    document.addEventListener('touchmove', onTouchMove, { passive: false });
    document.addEventListener('touchend', onTouchEnd);

    return () => {
        document.removeEventListener('touchmove', onTouchMove);
        document.removeEventListener('touchend', onTouchEnd);
    };
}
