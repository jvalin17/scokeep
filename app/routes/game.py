"""Game API routes — create, get state, end game, review phase."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.game import GameCreate, GameResponse
from app.services.game import GameService
from app.utils.auth import get_game_with_auth, require_auth

router = APIRouter(prefix="/api/game", tags=["game"])


@router.post("", status_code=201, response_model=GameResponse)
async def create_game(
    data: GameCreate,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    if data.playground_id != playground_id:
        raise HTTPException(status_code=403, detail="Access denied")
    game = await GameService.create(
        db=db,
        playground_id=playground_id,
        players=data.players,
        settings=data.settings.model_dump(),
    )
    return game


@router.get("/active/{playground_id}", response_model=GameResponse)
async def get_active_game(
    playground_id: int,
    auth_playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    if playground_id != auth_playground_id:
        raise HTTPException(status_code=403, detail="Access denied")
    game = await GameService.get_active_for_playground(db, playground_id)
    if not game:
        raise HTTPException(status_code=404, detail="No active game")
    return game


@router.get("/{game_id}", response_model=GameResponse)
async def get_game(
    game_id: int,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    game = await get_game_with_auth(db, game_id, playground_id)
    return game


@router.post("/{game_id}/next-round", response_model=GameResponse)
async def next_round(
    game_id: int,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    game = await get_game_with_auth(db, game_id, playground_id)
    if game.phase != "scoreboard":
        raise HTTPException(
            status_code=409,
            detail=f"Game is in '{game.phase}' phase, not 'scoreboard'",
        )

    await GameService.advance_round(db, game)
    return game


@router.post("/{game_id}/extend", response_model=GameResponse)
async def extend_game(
    game_id: int,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    game = await get_game_with_auth(db, game_id, playground_id)
    if game.status == "finished":
        raise HTTPException(status_code=409, detail="Game is already finished")
    if game.phase != "scoreboard":
        raise HTTPException(
            status_code=409,
            detail="Can only extend at scoreboard (between rounds)",
        )

    await GameService.extend_game(db, game)
    return game


@router.post("/{game_id}/end", response_model=GameResponse)
async def end_game(
    game_id: int,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    game = await get_game_with_auth(db, game_id, playground_id)
    if game.status == "finished":
        raise HTTPException(status_code=409, detail="Game is already finished")

    await GameService.end_game(db, game)
    return game


@router.post("/{game_id}/enter-review")
async def enter_review(
    game_id: int,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    game = await get_game_with_auth(db, game_id, playground_id)
    if game.phase != "scoreboard":
        raise HTTPException(
            status_code=409,
            detail=f"Game is in '{game.phase}' phase, not 'scoreboard'",
        )

    await GameService.update_phase(db, game, "review")
    return {"phase": game.phase}


@router.post("/{game_id}/rescore/{round_num}")
async def rescore_round(
    game_id: int,
    round_num: int,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Reset a specific round for re-entry of hands. Only works in review phase."""
    game = await get_game_with_auth(db, game_id, playground_id)
    if game.phase != "review":
        raise HTTPException(
            status_code=409,
            detail=f"Game is in '{game.phase}' phase, not 'review'",
        )

    try:
        await GameService.enter_review_rescore(db, game, round_num)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"phase": game.phase, "editing_round": round_num}


@router.post("/{game_id}/confirm-final", response_model=GameResponse)
async def confirm_final(
    game_id: int,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Finalize game from review phase — lock scores, compute insights."""
    game = await get_game_with_auth(db, game_id, playground_id)
    if game.phase != "review":
        raise HTTPException(
            status_code=409,
            detail=f"Game is in '{game.phase}' phase, not 'review'",
        )

    await GameService.confirm_final(db, game)
    return game
