import { describe, it, expect } from 'vitest';
import { renderPersonalityCards } from '../../app/static/js/components/personality-card.js';

function makePlayer(metaOverrides = {}) {
    return {
        personality: 'The Strategist',
        meta: {
            name: 'The Strategist',
            tagline: 'Plays with precision',
            color: '#43A047',
            icon: '🎯',
            ...metaOverrides,
        },
        accuracy_by_cards: {},
        insights: [],
        extras: {},
        games_analyzed: 5,
    };
}

describe('personality-card XSS prevention', () => {
    it('escapes meta.name containing script tag', () => {
        const html = renderPersonalityCards({
            Alice: makePlayer({ name: '<script>alert(1)</script>' }),
        });
        expect(html).not.toContain('<script>');
        expect(html).toContain('&lt;script&gt;');
    });

    it('escapes meta.icon containing img onerror', () => {
        const html = renderPersonalityCards({
            Bob: makePlayer({ icon: '<img onerror=alert(1)>' }),
        });
        expect(html).not.toContain('<img onerror');
        expect(html).toContain('&lt;img');
    });

    it('escapes meta.tagline containing HTML', () => {
        const html = renderPersonalityCards({
            Carol: makePlayer({ tagline: '<b onmouseover=alert(1)>hover</b>' }),
        });
        expect(html).not.toContain('<b onmouseover');
        expect(html).toContain('&lt;b');
    });

    it('validates meta.color rejects CSS injection', () => {
        const html = renderPersonalityCards({
            Dave: makePlayer({ color: 'red;background:url(evil)' }),
        });
        // Should not contain the injected CSS value
        expect(html).not.toContain('red;background:url(evil)');
    });

    it('allows valid hex color', () => {
        const html = renderPersonalityCards({
            Eve: makePlayer({ color: '#FF5722' }),
        });
        expect(html).toContain('--card-color: #FF5722');
    });
});
