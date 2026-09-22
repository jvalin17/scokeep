"""Sync API routes — receive client-side round/state data for server-side validation and storage."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.round import Round
from app.schemas.round import RoundResponse
from app.schemas.sync import SyncGameStateRequest, SyncRoundRequest
from app.services.scoring import assert_scores_match
from app.utils.auth import get_game_with_auth, require_auth
from app.utils.trump import get_cards_for_round, get_trump_for_round

router = APIRouter(prefix="/api/game", tags=["sync"])


DEFAULT_SCORING_FORMULA = "kachuful_standard"


async def _get_round_for_game(db: AsyncSession, game_id: int, round_num: int) -> Round | None:
    result = await db.execute(
        select(Round).where(Round.game_id == game_id, Round.round_num == round_num)
    )
    return result.scalar_one_or_none()


def _validate_round_metadata(body: SyncRoundRequest, game) -> None:
    """Raise 409 if cards_dealt or trump_suit don't match server-derived values."""
    rounds_per_set = game.settings.get("rounds_per_set", 8)
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


def _validate_round_keys(body: SyncRoundRequest, player_count: int) -> None:
    """Raise 409 if bids/hands_won keys don't match player indices or values out of bounds."""
    valid_keys = {str(i) for i in range(player_count)}
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


def _validate_scores(body: SyncRoundRequest, formula: str) -> None:
    """Raise 409/422 if client scores don't match server-derived scores."""
    try:
        assert_scores_match(body.bids, body.hands_won, formula, body.scores)
    except ValueError as exc:
        status = 422 if "Unknown scoring formula" in str(exc) else 409
        raise HTTPException(status_code=status, detail=str(exc)) from exc


async def _upsert_round(db: AsyncSession, game_id: int, body: SyncRoundRequest) -> Round:
    """Create or update a round row with fields from the sync body."""
    round_obj = await _get_round_for_game(db, game_id, body.round_num)
    if round_obj is None:
        round_obj = Round(game_id=game_id, round_num=body.round_num)
        db.add(round_obj)
    round_obj.cards_dealt = body.cards_dealt
    round_obj.trump_suit = body.trump_suit
    round_obj.bids = body.bids
    round_obj.hands_won = body.hands_won
    round_obj.scores = body.scores
    round_obj.status = body.status
    await db.commit()
    await db.refresh(round_obj)
    return round_obj


@router.post("/{game_id}/sync-round", response_model=RoundResponse)
async def sync_round(
    game_id: int,
    body: SyncRoundRequest,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Receive a completed round from the client, re-derive scores and upsert."""
    game = await get_game_with_auth(db, game_id, playground_id)
    _validate_round_metadata(body, game)
    _validate_round_keys(body, len(game.players))
    formula = game.settings.get("scoring_formula", DEFAULT_SCORING_FORMULA)
    _validate_scores(body, formula)
    return await _upsert_round(db, game_id, body)


@router.post("/{game_id}/sync-state")
async def sync_game_state(
    game_id: int,
    body: SyncGameStateRequest,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Receive client-side game state and update phase, round, dealer, status."""
    game = await get_game_with_auth(db, game_id, playground_id)

    game.phase = body.phase
    game.current_round = body.current_round
    game.dealer_index = body.dealer_index
    game.status = body.status

    await db.commit()
    await db.refresh(game)

    return {
        "id": game.id,
        "phase": game.phase,
        "current_round": game.current_round,
        "dealer_index": game.dealer_index,
        "status": game.status,
    }
