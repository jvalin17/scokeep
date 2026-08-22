"""Shared authentication utilities for route handlers.

Fixes BUG-006 (DRY: _require_auth duplicated in 3 files)
Fixes BUG-003 (cross-playground authorization)
"""

from fastapi import Cookie, HTTPException
from itsdangerous import BadSignature, URLSafeSerializer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.game import GameService

signer = URLSafeSerializer(settings.secret_key)


def require_auth(scokeep_session: str | None = Cookie(default=None)) -> int:
    """Extract and validate playground_id from session cookie."""
    if not scokeep_session:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = signer.loads(scokeep_session)
        return payload["playground_id"]
    except (BadSignature, KeyError) as exc:
        raise HTTPException(status_code=401, detail="Invalid session") from exc


async def get_game_with_auth(
    db: AsyncSession,
    game_id: int,
    playground_id: int,
):
    """Get game by ID and verify it belongs to the authenticated playground.

    Raises 404 if game not found, 403 if game belongs to different playground.
    """
    game = await GameService.get_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.playground_id != playground_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return game
