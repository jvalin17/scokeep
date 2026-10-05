/**
 * GameRegistry / Rule Pack dispatch tests.
 */
import { describe, it, expect } from 'vitest';
import { getPack, listPacks, routeFor, startRouteFor } from '../../app/static/js/packs/registry.js';

describe('GameRegistry', () => {
    it('getPack defaults unknown and missing to Judgement', () => {
        expect(getPack(undefined).id).toBe('kachuful');
        expect(getPack('nope').id).toBe('kachuful');
        expect(getPack('scoresheet').id).toBe('scoresheet');
    });

    it('listPacks includes judgement and scoresheet', () => {
        const ids = listPacks().map((pack) => pack.id).sort();
        expect(ids).toEqual(['kachuful', 'scoresheet']);
    });

    it('routeFor uses pack phase maps', () => {
        expect(routeFor({ phase: 'bidding', settings: { game_type: 'kachuful' } })).toBe('bid');
        expect(routeFor({ phase: 'entry', settings: { game_type: 'scoresheet' } })).toBe('entry');
        expect(routeFor({ phase: 'playing', settings: { game_type: 'scoresheet' } })).toBe(
            'scoreboard'
        );
    });

    it('startRouteFor Scoresheet is entry, Judgement is bid', () => {
        expect(startRouteFor('scoresheet')).toBe('entry');
        expect(startRouteFor('kachuful')).toBe('bid');
    });

    it('Scoresheet between-round actions include finished not only end_game', () => {
        const actions = getPack('scoresheet').betweenRoundActions;
        expect(actions).toContain('next_round');
        expect(actions).toContain('finished');
        expect(getPack('kachuful').betweenRoundActions).toContain('end_game');
    });
});
