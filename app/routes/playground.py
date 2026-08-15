"""Playground API routes — create, authenticate, get."""

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from itsdangerous import BadSignature, URLSafeSerializer
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.constants import (
    AUTH_RATE_LIMIT,
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_AUTH,
    SESSION_MAX_AGE_JOIN,
)
from app.database import get_db
from app.schemas.playground import PlaygroundAuth, PlaygroundCreate, PlaygroundResponse
from app.services.analytics import AnalyticsService
from app.services.playground import PlaygroundService

router = APIRouter(prefix="/api/playground", tags=["playground"])
limiter = Limiter(key_func=get_remote_address, enabled=settings.rate_limit_enabled)

signer = URLSafeSerializer(settings.secret_key)


def _get_authenticated_playground_id(
    scokeep_session: str | None = Cookie(default=None),
) -> int:
    if not scokeep_session:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = signer.loads(scokeep_session)
        return payload["playground_id"]
    except (BadSignature, KeyError) as exc:
        raise HTTPException(status_code=401, detail="Invalid session") from exc


@router.get("/recent")
async def list_recent_playgrounds(db: AsyncSession = Depends(get_db)):
    names = await PlaygroundService.list_recent_names(db)
    return {"names": names}


@router.post("", status_code=201, response_model=PlaygroundResponse)
async def create_playground(
    data: PlaygroundCreate,
    db: AsyncSession = Depends(get_db),
):
    playground = await PlaygroundService.create(
        db=db,
        name=data.name,
        pin=data.pin,
        players=data.players,
    )
    return playground


@router.post("/auth", response_model=PlaygroundResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def auth_playground(
    request: Request,
    data: PlaygroundAuth,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    playground = await PlaygroundService.get_by_name(db, data.name)
    if not playground:
        raise HTTPException(status_code=404, detail="Playground not found")

    if not PlaygroundService.verify_pin(playground, data.pin):
        raise HTTPException(status_code=401, detail="Invalid PIN")

    session_token = signer.dumps({"playground_id": playground.id})
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=True,
        max_age=SESSION_MAX_AGE_AUTH,
    )
    return playground


@router.post("/join/{share_code}", response_model=PlaygroundResponse)
async def join_live_game(
    share_code: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Join a live game by share code — no PIN needed if there's an active game."""
    playground = await PlaygroundService.get_by_share_code(db, share_code)
    if not playground:
        raise HTTPException(status_code=404, detail="Playground not found")

    from app.services.game import GameService
    active = await GameService.get_active_for_playground(db, playground.id)
    if not active:
        raise HTTPException(status_code=404, detail="No active game to join")

    session_token = signer.dumps({"playground_id": playground.id})
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=True,
        max_age=SESSION_MAX_AGE_JOIN,
    )
    return playground


@router.get("/{share_code}", response_model=PlaygroundResponse)
async def get_playground(
    share_code: str,
    playground_id: int = Depends(_get_authenticated_playground_id),
    db: AsyncSession = Depends(get_db),
):
    playground = await PlaygroundService.get_by_share_code(db, share_code)
    if not playground:
        raise HTTPException(status_code=404, detail="Playground not found")
    return playground


@router.get("/{share_code}/stats")
async def get_playground_stats(
    share_code: str,
    playground_id: int = Depends(_get_authenticated_playground_id),
    db: AsyncSession = Depends(get_db),
):
    playground = await PlaygroundService.get_by_share_code(db, share_code)
    if not playground:
        raise HTTPException(status_code=404, detail="Playground not found")
    if playground.id != playground_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return await AnalyticsService.get_playground_stats(
        db, playground.id, playground.insights,
    )


@router.delete("/{share_code}/stats")
async def clear_playground_stats(
    share_code: str,
    playground_id: int = Depends(_get_authenticated_playground_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete all finished games and rounds for this playground."""
    playground = await PlaygroundService.get_by_share_code(db, share_code)
    if not playground:
        raise HTTPException(status_code=404, detail="Playground not found")
    if playground.id != playground_id:
        raise HTTPException(status_code=403, detail="Access denied")
    count = await AnalyticsService.clear_stats(db, playground.id)
    return {"deleted_games": count}


@router.delete("")
async def delete_playground(
    data: PlaygroundAuth,
    db: AsyncSession = Depends(get_db),
):
    """Delete a playground and all its data. Requires name + PIN."""
    playground = await PlaygroundService.get_by_name(db, data.name)
    if not playground:
        raise HTTPException(status_code=404, detail="Playground not found")
    if not PlaygroundService.verify_pin(playground, data.pin):
        raise HTTPException(status_code=401, detail="Invalid PIN")
    await PlaygroundService.delete(db, playground)
    return {"deleted": playground.name}
