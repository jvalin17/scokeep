"""Playground API routes — create, authenticate, get."""

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from itsdangerous import BadSignature, URLSafeSerializer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.schemas.playground import PlaygroundAuth, PlaygroundCreate, PlaygroundResponse
from app.services.playground import PlaygroundService

router = APIRouter(prefix="/api/playground", tags=["playground"])

SESSION_COOKIE_NAME = "scokeep_session"
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
async def auth_playground(
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
        max_age=60 * 60 * 24 * 30,  # 30 days
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
