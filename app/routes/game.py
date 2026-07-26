"""Game API routes — create, get state, end game."""

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
    game = await GameService.create(
        db=db,
        playground_id=data.playground_id,
        players=data.players,
        settings=data.settings.model_dump(),
    )
    return game


@router.get("/active/{playground_id}", response_model=GameResponse)
async def get_active_game(
    playground_id: int,
    _auth_playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
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
