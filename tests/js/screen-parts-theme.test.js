import { describe, it, expect, beforeEach } from 'vitest';
import { setScreenContext } from '../../app/static/js/components/screen-parts.js';

describe('setScreenContext scoresheet theme', () => {
    beforeEach(() => {
        document.body.removeAttribute('data-phase');
        document.body.removeAttribute('data-appearance');
        document.body.removeAttribute('data-game-type');
    });

    it('marks scoresheet games so CSS can apply off-white navy theme', () => {
        setScreenContext('entry', {
            settings: { game_type: 'scoresheet', appearance: 'interactive' },
        });
        expect(document.body.getAttribute('data-phase')).toBe('entry');
        expect(document.body.getAttribute('data-appearance')).toBe('interactive');
        expect(document.body.getAttribute('data-game-type')).toBe('scoresheet');
    });

    it('defaults game type to kachuful for Judgement', () => {
        setScreenContext('bidding', {
            settings: { appearance: 'interactive' },
        });
        expect(document.body.getAttribute('data-game-type')).toBe('kachuful');
    });
});
