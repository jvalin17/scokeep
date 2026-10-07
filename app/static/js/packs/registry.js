/**
 * Pack registry — dispatch by settings.game_type.
 * Thin Rule Pack seam: packs own phase routes + start phase; shell owns IDB/sync/DOM.
 */
import { judgementPack } from './judgement/index.js';
import { scoresheetPack } from './scoresheet/index.js';

const PACKS = Object.freeze({
    [judgementPack.id]: judgementPack,
    [scoresheetPack.id]: scoresheetPack,
});

/**
 * @param {string|undefined|null} gameType
 * @returns {object}
 */
export function getPack(gameType) {
    const key = gameType || 'kachuful';
    return PACKS[key] || PACKS.kachuful;
}

/**
 * @returns {object[]}
 */
export function listPacks() {
    return Object.values(PACKS);
}

/**
 * @param {{ phase?: string, settings?: { game_type?: string } }} game
 * @returns {string} hash screen name
 */
export function routeFor(game) {
    const pack = getPack(game?.settings?.game_type);
    const phase = game?.phase || pack.startPhase;
    return pack.phaseRoutes[phase] || 'scoreboard';
}

/**
 * @param {string|undefined|null} gameType
 * @returns {string}
 */
export function startRouteFor(gameType) {
    const pack = getPack(gameType);
    return pack.phaseRoutes[pack.startPhase] || 'scoreboard';
}
