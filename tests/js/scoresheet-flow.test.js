/**
 * Scoresheet / Judgement flow — phase → hash route.
 * Pure map: no DOM, no network. Screens mount later onto these routes.
 */
import { describe, it, expect } from 'vitest';
import {
    JUDGEMENT_PHASE_ROUTES,
    SCORESHEET_PHASE_ROUTES,
    SCORESHEET_FLOW,
    routeForPhase,
    routeForGame,
    nextScoresheetPhase,
    isScoresheetGame,
} from '../../app/static/js/engine/scoresheet-flow.js';

describe('scoresheet-flow', () => {
    it('maps Scoresheet phases to routes without bid or play', () => {
        expect(routeForPhase('scoresheet', 'entry')).toBe('entry');
        expect(routeForPhase('scoresheet', 'round_review')).toBe('roundend');
        expect(routeForPhase('scoresheet', 'scoreboard')).toBe('scoreboard');
        expect(routeForPhase('scoresheet', 'intermission')).toBe('scoreboard');
        expect(routeForPhase('scoresheet', 'review')).toBe('review');
        expect(routeForPhase('scoresheet', 'final')).toBe('final');

        expect(Object.values(SCORESHEET_PHASE_ROUTES)).not.toContain('bid');
        expect(Object.values(SCORESHEET_PHASE_ROUTES)).not.toContain('play');
    });

    it('keeps Judgement bidding and playing routes', () => {
        expect(routeForPhase('kachuful', 'bidding')).toBe('bid');
        expect(routeForPhase('kachuful', 'playing')).toBe('play');
        expect(routeForPhase('kachuful', 'round_end')).toBe('roundend');
        expect(JUDGEMENT_PHASE_ROUTES.bidding).toBe('bid');
    });

    it('routeForGame selects by game_type', () => {
        expect(
            routeForGame({ phase: 'entry', settings: { game_type: 'scoresheet' } })
        ).toBe('entry');
        expect(
            routeForGame({ phase: 'bidding', settings: { game_type: 'kachuful' } })
        ).toBe('bid');
        expect(routeForGame({ phase: 'bidding', settings: {} })).toBe('bid');
        expect(routeForGame({ phase: 'nope', settings: { game_type: 'scoresheet' } })).toBe(
            'scoreboard'
        );
    });

    it('nextScoresheetPhase advances the play loop', () => {
        expect(SCORESHEET_FLOW).toEqual([
            'entry',
            'round_review',
            'scoreboard',
            'entry',
        ]);
        expect(nextScoresheetPhase('entry')).toBe('round_review');
        expect(nextScoresheetPhase('round_review')).toBe('scoreboard');
        expect(nextScoresheetPhase('scoreboard')).toBe('entry');
        expect(nextScoresheetPhase('intermission')).toBe('entry');
        expect(nextScoresheetPhase('review')).toBeNull();
    });

    it('isScoresheetGame reads settings.game_type', () => {
        expect(isScoresheetGame({ settings: { game_type: 'scoresheet' } })).toBe(true);
        expect(isScoresheetGame({ settings: { game_type: 'kachuful' } })).toBe(false);
        expect(isScoresheetGame({})).toBe(false);
    });
});
