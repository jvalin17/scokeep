/**
 * Scoresheet pack — open-ended name→score rounds (Declare / mini golf / house).
 */
import {
    SCORESHEET_PHASE_ROUTES,
    nextScoresheetPhase,
} from '../../engine/scoresheet-flow.js';

export const scoresheetPack = Object.freeze({
    id: 'scoresheet',
    displayName: 'Scoresheet',
    startPhase: 'entry',
    phaseRoutes: SCORESHEET_PHASE_ROUTES,
    settingsDefaults: {
        game_type: 'scoresheet',
        label: '',
        winner: 'highest',
        show_totals: true,
        allow_negatives: false,
        appearance: 'interactive',
    },
    betweenRoundActions: Object.freeze(['next_round', 'finished', 'undo', 'edit']),
    awardsGate: 'scoresheet_light',
    nextPhase: nextScoresheetPhase,
});
