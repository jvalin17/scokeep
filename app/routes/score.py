"""Scoreboard API routes — scores, history, undo, admin correction."""

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.round import Round
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


class ScoreCorrectionRequest(BaseModel):
    player_index: int
    score: int


@router.patch("/{game_id}/round/{round_num}/score")
async def correct_score(
    game_id: int,
    round_num: int,
    body: ScoreCorrectionRequest,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    x_admin_key: str = Header(default=""),
):
    if not settings.admin_key or not hmac.compare_digest(x_admin_key, settings.admin_key):
        raise HTTPException(status_code=403, detail="Admin key required")
    game = await get_game_with_auth(db, game_id, playground_id)
    if body.player_index < 0 or body.player_index >= len(game.players):
        raise HTTPException(status_code=400, detail="Invalid player index")

    result = await db.execute(
        select(Round).where(
            Round.game_id == game_id, Round.round_num == round_num,
        )
    )
    rnd = result.scalar_one_or_none()
    if not rnd:
        raise HTTPException(status_code=404, detail="Round not found")

    updated_scores = {**rnd.scores, str(body.player_index): body.score}
    rnd.scores = updated_scores
    await db.commit()

    return {"status": "corrected", "round_num": round_num, "updated_score": body.score}
