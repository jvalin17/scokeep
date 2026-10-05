"""Scoresheet Rule Pack — direct per-player integer scores, open-ended rounds."""

from __future__ import annotations

from fastapi import HTTPException

from app.constants import DEFAULT_APPEARANCE
from app.models.game import Game
from app.schemas.sync import SyncRoundRequest
from app.services.packs import (
    AWARDS_GATE_SCORESHEET_LIGHT,
    OPEN_ENDED_ROUND_CAP_STEP,
    ROUND_META_NOT_APPLICABLE,
    SCORESHEET_MAX_ABS_SCORE,
    GamePack,
)

_SETTINGS_DEFAULTS = {
    "game_type": "scoresheet",
    "winner": "highest",
    "show_totals": True,
    "allow_negatives": False,
    "label": "",
    "appearance": DEFAULT_APPEARANCE,
}

_ALLOWED_PHASES = frozenset(
    {
        "entry",
        "round_review",
        "scoreboard",
        "intermission",
        "review",
        "final",
    }
)


def _merge_settings(client_settings: dict) -> dict:
    merged = {**_SETTINGS_DEFAULTS, **client_settings}
    merged["game_type"] = "scoresheet"
    # Normalize label length for storage safety
    label = merged.get("label") or ""
    if not isinstance(label, str):
        label = str(label)
    merged["label"] = label.strip()[:80]
    if merged.get("winner") not in ("highest", "lowest"):
        merged["winner"] = "highest"
    merged["show_totals"] = bool(merged.get("show_totals", True))
    merged["allow_negatives"] = bool(merged.get("allow_negatives", False))
    return merged


def _initial_total_rounds(_settings: dict) -> int:
    return OPEN_ENDED_ROUND_CAP_STEP


def _next_phase_on_advance(_game: Game) -> str:
    return "entry"


def _grow_total_rounds_if_needed(game: Game) -> None:
    if game.current_round >= game.total_rounds - 1:
        game.total_rounds += OPEN_ENDED_ROUND_CAP_STEP


def _validate_sync_round(game: Game, body: SyncRoundRequest) -> None:
    """Trust-boundary checks for Scoresheet rounds — never trust raw client scores."""
    player_count = len(game.players)
    valid_keys = {str(index) for index in range(player_count)}
    if set(body.scores.keys()) != valid_keys:
        raise HTTPException(409, detail=f"scores keys must be {valid_keys}")

    allow_negatives = bool(game.settings.get("allow_negatives", False))
    for player_key, score in body.scores.items():
        if not isinstance(score, int) or isinstance(score, bool):
            raise HTTPException(409, detail=f"score for {player_key} must be an integer")
        if abs(score) > SCORESHEET_MAX_ABS_SCORE:
            raise HTTPException(
                409,
                detail=f"score {score} exceeds ±{SCORESHEET_MAX_ABS_SCORE}",
            )
        if score < 0 and not allow_negatives:
            raise HTTPException(409, detail="negative scores are not allowed for this game")

    # Scoresheet does not use bids/hands/trump — reject Judgement-shaped payloads
    if body.bids:
        raise HTTPException(409, detail="Scoresheet rounds must not include bids")
    if body.hands_won:
        raise HTTPException(409, detail="Scoresheet rounds must not include hands_won")
    if body.trump_suit not in (ROUND_META_NOT_APPLICABLE, "none", ""):
        raise HTTPException(
            409,
            detail=f"Scoresheet trump_suit must be '{ROUND_META_NOT_APPLICABLE}'",
        )
    if body.cards_dealt not in (0, 1):
        raise HTTPException(409, detail="Scoresheet cards_dealt must be 0 or 1")


scoresheet_pack = GamePack(
    id="scoresheet",
    display_name="Scoresheet",
    start_phase="entry",
    settings_defaults=dict(_SETTINGS_DEFAULTS),
    awards_gate=AWARDS_GATE_SCORESHEET_LIGHT,
    supports_extend=False,
    allowed_phases=_ALLOWED_PHASES,
    merge_settings=_merge_settings,
    initial_total_rounds=_initial_total_rounds,
    next_phase_on_advance=_next_phase_on_advance,
    grow_total_rounds_if_needed=_grow_total_rounds_if_needed,
    validate_sync_round=_validate_sync_round,
    should_compute_judgement_insights=False,
)
