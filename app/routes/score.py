"""Scoreboard API routes — scores, history, undo."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.scoreboard import ScoreboardService
from app.utils.auth import get_game_with_auth, require_auth

router = APIRouter(prefix="/api/game", tags=["scoreboard"])


@router.get("/{game_id}/scoreboard")
async def get_scoreboard(
    game_id: int,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    game = await get_game_with_auth(db, game_id, playground_id)

    scoreboard = await ScoreboardService.get_scoreboard(
        db, game_id, player_count=len(game.players),
    )
    return scoreboard


@router.get("/{game_id}/history")
async def get_history(
    game_id: int,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    await get_game_with_auth(db, game_id, playground_id)

    return await ScoreboardService.get_history(db, game_id)


@router.post("/{game_id}/undo")
async def undo_last_round(
    game_id: int,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    game = await get_game_with_auth(db, game_id, playground_id)

    try:
        await ScoreboardService.undo_last_round(db, game)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "undone", "current_round": game.current_round}
