"""Judgement (kachuful) Rule Pack — bid/play/hands scoring."""

from __future__ import annotations

from fastapi import HTTPException

from app.constants import (
    DEFAULT_APPEARANCE,
    DEFAULT_MODE,
    DEFAULT_MUST_LOSE,
    DEFAULT_NUM_SETS,
    DEFAULT_ROUNDS_PER_SET,
    DEFAULT_SCORING_FORMULA,
    DEFAULT_TIMER_SECONDS,
    TRUMP_ORDER,
)
from app.models.game import Game
from app.schemas.sync import SyncRoundRequest
from app.services.packs import (
    AWARDS_GATE_JUDGEMENT_ML,
    GamePack,
)
from app.services.scoring import assert_scores_match
from app.utils.trump import get_cards_for_round, get_trump_for_round

_SETTINGS_DEFAULTS = {
    "game_type": "kachuful",
    "mode": DEFAULT_MODE,
    "appearance": DEFAULT_APPEARANCE,
    "timer_seconds": DEFAULT_TIMER_SECONDS,
    "scoring_formula": DEFAULT_SCORING_FORMULA,
    "num_sets": DEFAULT_NUM_SETS,
    "rounds_per_set": DEFAULT_ROUNDS_PER_SET,
    "must_lose": DEFAULT_MUST_LOSE,
    "trump_rotation": TRUMP_ORDER,
}

_ALLOWED_PHASES = frozenset(
    {
        "bidding",
        "playing",
        "round_end",
        "scoring",
        "scoreboard",
        "review",
        "final",
    }
)


def _merge_settings(client_settings: dict) -> dict:
    merged = {**_SETTINGS_DEFAULTS, **client_settings}
    merged["game_type"] = "kachuful"
    return merged


def _initial_total_rounds(settings: dict) -> int:
    num_sets = int(settings.get("num_sets", DEFAULT_NUM_SETS))
    rounds_per_set = int(settings.get("rounds_per_set", DEFAULT_ROUNDS_PER_SET))
    return num_sets * rounds_per_set


def _next_phase_on_advance(_game: Game) -> str:
    """Phase after incrementing round counter (review is handled before increment)."""
    return "bidding"


def _grow_total_rounds_if_needed(game: Game) -> None:
    return


def _validate_sync_round(game: Game, body: SyncRoundRequest) -> None:
    rounds_per_set = game.settings.get("rounds_per_set", DEFAULT_ROUNDS_PER_SET)
    expected_cards = get_cards_for_round(body.round_num, rounds_per_set)
    expected_trump = get_trump_for_round(body.round_num)
    if body.cards_dealt != expected_cards:
        raise HTTPException(
            409,
            detail=f"cards_dealt mismatch: got {body.cards_dealt}, expected {expected_cards}",
        )
    if body.trump_suit != expected_trump:
        raise HTTPException(
            409,
            detail=f"trump_suit mismatch: got {body.trump_suit}, expected {expected_trump}",
        )

    player_count = len(game.players)
    valid_keys = {str(index) for index in range(player_count)}
    if set(body.bids.keys()) != valid_keys:
        raise HTTPException(409, detail=f"bids keys must be {valid_keys}")
    if set(body.hands_won.keys()) != valid_keys:
        raise HTTPException(409, detail=f"hands_won keys must be {valid_keys}")
    for bid in body.bids.values():
        if bid < 0 or bid > body.cards_dealt:
            raise HTTPException(409, detail=f"bid {bid} out of range 0..{body.cards_dealt}")
    for hands in body.hands_won.values():
        if hands < 0:
            raise HTTPException(409, detail="hands_won cannot be negative")
    if sum(body.hands_won.values()) > body.cards_dealt:
        raise HTTPException(409, detail="hands_won sum exceeds cards_dealt")

    formula = game.settings.get("scoring_formula", DEFAULT_SCORING_FORMULA)
    try:
        assert_scores_match(body.bids, body.hands_won, formula, body.scores)
    except ValueError as exc:
        status = 422 if "Unknown scoring formula" in str(exc) else 409
        raise HTTPException(status_code=status, detail=str(exc)) from exc


judgement_pack = GamePack(
    id="kachuful",
    display_name="Judgement",
    start_phase="bidding",
    settings_defaults=dict(_SETTINGS_DEFAULTS),
    awards_gate=AWARDS_GATE_JUDGEMENT_ML,
    supports_extend=True,
    allowed_phases=_ALLOWED_PHASES,
    merge_settings=_merge_settings,
    initial_total_rounds=_initial_total_rounds,
    next_phase_on_advance=_next_phase_on_advance,
    grow_total_rounds_if_needed=_grow_total_rounds_if_needed,
    validate_sync_round=_validate_sync_round,
    should_compute_judgement_insights=True,
)
