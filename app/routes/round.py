"""Round API routes — bidding, hands entry, round lifecycle."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.round import BidEdit, BidSubmit, HandsSubmit, RoundResponse
from app.services.game import GameService
from app.services.round import RoundService
from app.utils.auth import get_game_with_auth, require_auth

router = APIRouter(prefix="/api/game", tags=["round"])


async def _get_game_and_round(db: AsyncSession, game_id: int, playground_id: int):
    """Get game (with auth check) and current round, creating round if needed."""
    game = await get_game_with_auth(db, game_id, playground_id)

    round_obj = await RoundService.get_current_round(db, game.id, game.current_round)
    if not round_obj:
        round_obj = await RoundService.create_round(db, game)

    return game, round_obj


@router.post("/{game_id}/bid", response_model=RoundResponse)
async def submit_bid(
    game_id: int,
    data: BidSubmit,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    game, round_obj = await _get_game_and_round(db, game_id, playground_id)

    if game.phase != "bidding":
        raise HTTPException(
            status_code=409,
            detail=f"Game is in '{game.phase}' phase, not 'bidding'",
        )

    must_lose = game.settings.get("must_lose", False)
    try:
        await RoundService.submit_bid(
            db, round_obj,
            player_index=data.player_index,
            value=data.value,
            must_lose=must_lose,
            cards_dealt=round_obj.cards_dealt,
            player_count=len(game.players),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return round_obj


@router.get("/{game_id}/bids", response_model=RoundResponse)
async def get_bids(
    game_id: int,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    game, round_obj = await _get_game_and_round(db, game_id, playground_id)
    return round_obj


@router.patch("/{game_id}/bid/{player_index}", response_model=RoundResponse)
async def edit_bid(
    game_id: int,
    player_index: int,
    data: BidEdit,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    game, round_obj = await _get_game_and_round(db, game_id, playground_id)

    try:
        await RoundService.edit_bid(db, round_obj, player_index=player_index, value=data.value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return round_obj


@router.post("/{game_id}/start-round")
async def start_round(
    game_id: int,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    game, round_obj = await _get_game_and_round(db, game_id, playground_id)

    if game.phase != "bidding":
        raise HTTPException(
            status_code=409,
            detail=f"Game is in '{game.phase}' phase, not 'bidding'",
        )

    player_count = len(game.players)
    try:
        await RoundService.confirm_bids(db, round_obj, player_count)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await GameService.update_phase(db, game, "playing")
    return {"phase": game.phase}


@router.post("/{game_id}/enter-round-end")
async def enter_round_end(
    game_id: int,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    game, round_obj = await _get_game_and_round(db, game_id, playground_id)

    if game.phase != "playing":
        raise HTTPException(status_code=409, detail=f"Game is in '{game.phase}', not 'playing'")

    round_obj.status = "round_end"
    await db.commit()
    await GameService.update_phase(db, game, "round_end")
    return {"phase": game.phase}


@router.post("/{game_id}/hands", response_model=RoundResponse)
async def submit_hands(
    game_id: int,
    data: HandsSubmit,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    game, round_obj = await _get_game_and_round(db, game_id, playground_id)

    if game.phase != "round_end":
        raise HTTPException(
            status_code=409,
            detail=f"Game is in '{game.phase}' phase, not 'round_end'",
        )

    try:
        await RoundService.submit_hands(
            db, round_obj, player_index=data.player_index, value=data.value,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return round_obj


@router.post("/{game_id}/end-round", response_model=RoundResponse)
async def end_round(
    game_id: int,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    game, round_obj = await _get_game_and_round(db, game_id, playground_id)
    player_count = len(game.players)
    formula = game.settings.get("scoring_formula", "kachuful_standard")

    try:
        await RoundService.end_round(db, round_obj, player_count, formula)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await GameService.update_phase(db, game, "scoreboard")
    return round_obj
