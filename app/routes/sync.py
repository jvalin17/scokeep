"""Sync API routes — receive client-side round/state data for validation and storage."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import GAME_RATE_LIMIT
from app.database import get_db
from app.models.round import Round
from app.routes.playground import limiter
from app.schemas.round import RoundResponse
from app.schemas.sync import SyncGameStateRequest, SyncRoundRequest
from app.services.packs.registry import ROUND_META_NOT_APPLICABLE, get_pack_for_settings
from app.utils.auth import get_game_with_auth, require_auth

router = APIRouter(prefix="/api/game", tags=["sync"])


async def _get_round_for_game(db: AsyncSession, game_id: int, round_num: int) -> Round | None:
    result = await db.execute(
        select(Round).where(Round.game_id == game_id, Round.round_num == round_num)
    )
    return result.scalar_one_or_none()


async def _upsert_round(db: AsyncSession, game_id: int, body: SyncRoundRequest) -> Round:
    """Create or update a round row with fields from the sync body."""
    round_obj = await _get_round_for_game(db, game_id, body.round_num)
    if round_obj is None:
        round_obj = Round(game_id=game_id, round_num=body.round_num)
        db.add(round_obj)

    trump_suit = body.trump_suit
    if trump_suit in ("none", ""):
        trump_suit = ROUND_META_NOT_APPLICABLE

    round_obj.cards_dealt = body.cards_dealt
    round_obj.trump_suit = trump_suit
    round_obj.bids = body.bids
    round_obj.hands_won = body.hands_won
    round_obj.scores = body.scores
    # Client engine uses "complete"; server analytics/insights expect "scored"
    round_obj.status = "scored" if body.status == "complete" else body.status
    await db.commit()
    await db.refresh(round_obj)
    return round_obj


@router.post("/{game_id}/sync-round", response_model=RoundResponse)
@limiter.limit(GAME_RATE_LIMIT)
async def sync_round(
    request: Request,
    game_id: int,
    body: SyncRoundRequest,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Receive a completed round from the client; pack validates then upsert."""
    game = await get_game_with_auth(db, game_id, playground_id)
    if game.status == "finished":
        raise HTTPException(409, detail="Cannot sync rounds to a finished game")

    pack = get_pack_for_settings(game.settings)
    pack.validate_sync_round(game, body)
    return await _upsert_round(db, game_id, body)


@router.post("/{game_id}/sync-state")
@limiter.limit(GAME_RATE_LIMIT)
async def sync_game_state(
    request: Request,
    game_id: int,
    body: SyncGameStateRequest,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Receive client-side game state and update phase, round, dealer, status."""
    game = await get_game_with_auth(db, game_id, playground_id)
    if game.status == "finished":
        raise HTTPException(409, detail="Cannot sync state to a finished game")

    pack = get_pack_for_settings(game.settings)
    if body.phase not in pack.allowed_phases:
        raise HTTPException(
            409,
            detail=f"Phase '{body.phase}' is not valid for {pack.display_name}",
        )

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
