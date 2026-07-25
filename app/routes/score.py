"""Scoreboard API routes — scores, history, undo."""

from fastapi import APIRouter, Cookie, Depends, HTTPException
from itsdangerous import BadSignature, URLSafeSerializer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.game import GameService
from app.services.scoreboard import ScoreboardService

router = APIRouter(prefix="/api/game", tags=["scoreboard"])

signer = URLSafeSerializer(settings.secret_key)


def _require_auth(scokeep_session: str | None = Cookie(default=None)) -> int:
    if not scokeep_session:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = signer.loads(scokeep_session)
        return payload["playground_id"]
    except (BadSignature, KeyError) as exc:
        raise HTTPException(status_code=401, detail="Invalid session") from exc


@router.get("/{game_id}/scoreboard")
async def get_scoreboard(
    game_id: int,
    playground_id: int = Depends(_require_auth),
    db: AsyncSession = Depends(get_db),
):
    game = await GameService.get_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    scoreboard = await ScoreboardService.get_scoreboard(
        db, game_id, player_count=len(game.players),
    )
    return scoreboard


@router.get("/{game_id}/history")
async def get_history(
    game_id: int,
    playground_id: int = Depends(_require_auth),
    db: AsyncSession = Depends(get_db),
):
    game = await GameService.get_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    return await ScoreboardService.get_history(db, game_id)


@router.post("/{game_id}/undo")
async def undo_last_round(
    game_id: int,
    playground_id: int = Depends(_require_auth),
    db: AsyncSession = Depends(get_db),
):
    game = await GameService.get_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    try:
        await ScoreboardService.undo_last_round(db, game)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "undone", "current_round": game.current_round}
