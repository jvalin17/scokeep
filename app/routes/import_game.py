"""Import endpoint — receive offline Quick Game data and store in server DB.

POST /api/game/{share_code}/import
- Auth: session cookie (require_auth)
- Dedup: client_game_id (idempotent — returns existing game on duplicate)
- Validates: re-derives scores from bids + hands_won
- Creates: Game + Round records in one transaction
- Triggers: compute_insights (fire-and-forget)
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.game import Game
from app.models.round import Round
from app.schemas.import_game import ImportGameRequest, ImportGameResponse
from app.services.playground import PlaygroundService
from app.services.scoring import calculate_round_scores
from app.utils.auth import require_auth

logger = logging.getLogger("scokeep.import")

router = APIRouter(prefix="/api/game", tags=["import"])

DEFAULT_FORMULA = "kachuful_standard"
ALLOWED_FORMULAS = {"kachuful_standard", "kachuful_zeros"}


async def _check_duplicate(
    db: AsyncSession, client_game_id: str, playground_id: int, round_count: int,
) -> ImportGameResponse | None:
    """Return an idempotent response if this game was already imported."""
    result = await db.execute(
        select(Game).where(
            Game.client_game_id == client_game_id,
            Game.playground_id == playground_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return ImportGameResponse(
            game_id=existing.id, rounds_imported=round_count, already_existed=True,
        )
    return None


def _validate_round_scores(rounds, formula: str) -> None:
    """Raise 422 if any round has tampered scores."""
    for round_data in rounds:
        expected = calculate_round_scores(
            round_data.bids, round_data.hands_won, formula,
        )
        if round_data.scores and round_data.scores != expected:
            raise HTTPException(
                status_code=422,
                detail=f"Score mismatch in round {round_data.round_num}: "
                f"expected {expected}, got {round_data.scores}",
            )


def _build_game(body: ImportGameRequest, playground_id: int) -> Game:
    """Create a Game model from import payload."""
    total = len(body.rounds)
    return Game(
        playground_id=playground_id, players=body.players, settings=body.settings,
        current_round=total, total_rounds=total, phase="finished", dealer_index=0,
        status="finished", started_at=body.started_at, finished_at=body.finished_at,
        client_game_id=body.client_game_id, source="offline_import",
    )


async def _create_game_with_rounds(
    db: AsyncSession, body: ImportGameRequest, playground_id: int, formula: str,
) -> Game:
    """Insert Game + Round records in one transaction, return the Game."""
    game = _build_game(body, playground_id)
    db.add(game)
    await db.flush()
    for rd in body.rounds:
        scores = calculate_round_scores(rd.bids, rd.hands_won, formula)
        db.add(Round(
            game_id=game.id, round_num=rd.round_num, cards_dealt=rd.cards_dealt,
            trump_suit=rd.trump_suit, bids=rd.bids, hands_won=rd.hands_won,
            scores=scores, status="complete",
        ))
    await db.commit()
    return game


async def _resolve_playground(db: AsyncSession, share_code: str, playground_id: int):
    """Resolve share_code to playground, verify session ownership."""
    playground = await PlaygroundService.get_by_share_code(db, share_code)
    if not playground:
        raise HTTPException(status_code=404, detail="Room not found")
    if playground.id != playground_id:
        raise HTTPException(status_code=403, detail="Access denied — wrong room session")
    return playground


def _schedule_insights_recompute(background_tasks: BackgroundTasks, playground_id: int):
    """Schedule fire-and-forget insights recompute."""
    async def _run():
        try:
            from app.database import async_session_factory
            from app.services.insights import compute_insights
            async with async_session_factory() as fresh_db:
                await compute_insights(fresh_db, playground_id)
        except Exception:
            logger.warning("Insights recompute failed after import (non-fatal)", exc_info=True)
    background_tasks.add_task(_run)


@router.post("/{share_code}/import", response_model=ImportGameResponse)
async def import_game(
    share_code: str,
    body: ImportGameRequest,
    background_tasks: BackgroundTasks,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Import an offline Quick Game into a room's game history."""
    playground = await _resolve_playground(db, share_code, playground_id)

    duplicate = await _check_duplicate(db, body.client_game_id, playground.id, len(body.rounds))
    if duplicate:
        return duplicate

    formula = body.settings.get("scoring_formula", DEFAULT_FORMULA)
    if formula not in ALLOWED_FORMULAS:
        raise HTTPException(status_code=422, detail=f"Unknown scoring formula: {formula}")
    _validate_round_scores(body.rounds, formula)
    game = await _create_game_with_rounds(db, body, playground.id, formula)

    _schedule_insights_recompute(background_tasks, playground.id)
    return ImportGameResponse(game_id=game.id, rounds_imported=len(body.rounds))
