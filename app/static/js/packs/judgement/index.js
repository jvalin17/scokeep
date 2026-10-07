/**
 * Judgement (kachuful) pack — wraps existing bid/play phases; does not rewrite screens.
 */
import { JUDGEMENT_PHASE_ROUTES } from '../../engine/scoresheet-flow.js';

export const judgementPack = Object.freeze({
    id: 'kachuful',
    displayName: 'Judgement',
    startPhase: 'bidding',
    phaseRoutes: JUDGEMENT_PHASE_ROUTES,
    settingsDefaults: {
        game_type: 'kachuful',
        mode: 'rookie',
        appearance: 'interactive',
    },
    /** Between-round CTAs — Judgement uses End Game on scoreboard (existing). */
    betweenRoundActions: Object.freeze(['next_round', 'end_game', 'undo', 'edit']),
    awardsGate: 'judgement_ml',
});
