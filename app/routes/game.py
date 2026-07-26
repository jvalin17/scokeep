"""Game API routes — create, get state, end game."""

from fastapi import APIRouter, Cookie, Depends, HTTPException
from itsdangerous import BadSignature, URLSafeSerializer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.schemas.game import GameCreate, GameResponse
from app.services.game import GameService

router = APIRouter(prefix="/api/game", tags=["game"])

signer = URLSafeSerializer(settings.secret_key)


def _require_auth(scokeep_session: str | None = Cookie(default=None)) -> int:
    if not scokeep_session:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = signer.loads(scokeep_session)
        return payload["playground_id"]
    except (BadSignature, KeyError) as exc:
        raise HTTPException(status_code=401, detail="Invalid session") from exc


@router.post("", status_code=201, response_model=GameResponse)
async def create_game(
    data: GameCreate,
    playground_id: int = Depends(_require_auth),
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
    _auth_playground_id: int = Depends(_require_auth),
    db: AsyncSession = Depends(get_db),
):
    game = await GameService.get_active_for_playground(db, playground_id)
    if not game:
        raise HTTPException(status_code=404, detail="No active game")
    return game


@router.get("/{game_id}", response_model=GameResponse)
async def get_game(
    game_id: int,
    playground_id: int = Depends(_require_auth),
    db: AsyncSession = Depends(get_db),
):
    game = await GameService.get_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@router.post("/{game_id}/next-round", response_model=GameResponse)
async def next_round(
    game_id: int,
    playground_id: int = Depends(_require_auth),
    db: AsyncSession = Depends(get_db),
):
    game = await GameService.get_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.phase != "scoreboard":
        raise HTTPException(
            status_code=409,
            detail=f"Game is in '{game.phase}' phase, not 'scoreboard'",
        )

    await GameService.advance_round(db, game)
    return game


@router.post("/{game_id}/end", response_model=GameResponse)
async def end_game(
    game_id: int,
    playground_id: int = Depends(_require_auth),
    db: AsyncSession = Depends(get_db),
):
    game = await GameService.get_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.status == "finished":
        raise HTTPException(status_code=409, detail="Game is already finished")

    await GameService.end_game(db, game)
    return game
