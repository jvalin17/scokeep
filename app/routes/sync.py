"""Sync API routes — receive client-side round/state data for server-side validation and storage."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.round import Round
from app.schemas.round import RoundResponse
from app.schemas.sync import SyncGameStateRequest, SyncRoundRequest
from app.services.scoring import calculate_round_scores
from app.utils.auth import get_game_with_auth, require_auth
from app.utils.trump import get_cards_for_round, get_trump_for_round

router = APIRouter(prefix="/api/game", tags=["sync"])


DEFAULT_SCORING_FORMULA = "kachuful_standard"


async def _get_round_for_game(db: AsyncSession, game_id: int, round_num: int) -> Round | None:
    result = await db.execute(
        select(Round).where(
            Round.game_id == game_id,
            Round.round_num == round_num,
        )
    )
    return result.scalar_one_or_none()


@router.post("/{game_id}/sync-round", response_model=RoundResponse)
async def sync_round(
    game_id: int,
    body: SyncRoundRequest,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Receive a completed round from the client, re-derive scores and upsert."""
    # 1. Validate game exists and belongs to this playground
    game = await get_game_with_auth(db, game_id, playground_id)

    # 1b. Validate cards_dealt and trump_suit match server-derived values
    rounds_per_set = game.settings.get("rounds_per_set", 8)
    expected_cards = get_cards_for_round(body.round_num, rounds_per_set)
    expected_trump = get_trump_for_round(body.round_num)
    if body.cards_dealt != expected_cards:
        raise HTTPException(
            status_code=409,
            detail=f"cards_dealt mismatch: got {body.cards_dealt}, expected {expected_cards}",
        )
    if body.trump_suit != expected_trump:
        raise HTTPException(
            status_code=409,
            detail=f"trump_suit mismatch: got {body.trump_suit}, expected {expected_trump}",
        )

    # 2. Re-derive scores from bids + hands_won using server-side scoring
    formula = game.settings.get("scoring_formula", DEFAULT_SCORING_FORMULA)
    try:
        derived_scores = calculate_round_scores(body.bids, body.hands_won, formula)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # 3. Compare with client-submitted scores — reject on mismatch
    if derived_scores != body.scores:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Score mismatch: client sent {body.scores} but server derived {derived_scores}"
            ),
        )

    # 4. Upsert Round row
    round_obj = await _get_round_for_game(db, game_id, body.round_num)
    if round_obj is None:
        round_obj = Round(
            game_id=game_id,
            round_num=body.round_num,
            cards_dealt=body.cards_dealt,
            trump_suit=body.trump_suit,
            bids=body.bids,
            hands_won=body.hands_won,
            scores=body.scores,
            status=body.status,
        )
        db.add(round_obj)
    else:
        round_obj.cards_dealt = body.cards_dealt
        round_obj.trump_suit = body.trump_suit
        round_obj.bids = body.bids
        round_obj.hands_won = body.hands_won
        round_obj.scores = body.scores
        round_obj.status = body.status

    await db.commit()
    await db.refresh(round_obj)

    # 5. Return 200 with round data
    return round_obj


@router.post("/{game_id}/sync-state")
async def sync_game_state(
    game_id: int,
    body: SyncGameStateRequest,
    playground_id: int = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Receive client-side game state and update phase, round, dealer, status."""
    game = await get_game_with_auth(db, game_id, playground_id)

    game.phase = body.phase
    game.current_round = body.current_round
    game.dealer_index = body.dealer_index
    game.status = body.status

    await db.commit()
    await db.refresh(game)

    return {
        "id": game.id,
        "phase": game.phase,
        "current_round": game.current_round,
        "dealer_index": game.dealer_index,
        "status": game.status,
    }
