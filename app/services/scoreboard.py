"""Scoreboard service — cumulative scores, history, undo."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.round import Round


def compute_scoreboard(rounds: list[dict], player_count: int = 0) -> dict:
    """Pure function: compute cumulative totals from a list of scored round dicts.

    Each round dict must have a 'scores' key mapping player_key -> score int.
    Other fields (round_num, cards_dealt, trump_suit, bids, hands_won) are
    passed through unchanged in the returned rounds list.

    Args:
        rounds: List of round dicts with scores and metadata.
        player_count: Ensures players 0..player_count-1 appear in totals (value 0).

    Returns:
        {"totals": {player_key: cumulative_score}, "rounds": [round_dict, ...]}
    """
    totals: dict[str, int] = {}
    rounds_data = []

    for round_dict in rounds:
        rounds_data.append(dict(round_dict))
        for player_key, score in round_dict["scores"].items():
            totals[player_key] = totals.get(player_key, 0) + score

    for i in range(player_count):
        totals.setdefault(str(i), 0)

    return {"totals": totals, "rounds": rounds_data}


def _round_to_dict(round_obj) -> dict:
    """Project a Round ORM object to a plain dict."""
    return {
        "round_num": round_obj.round_num,
        "cards_dealt": round_obj.cards_dealt,
        "trump_suit": round_obj.trump_suit,
        "bids": round_obj.bids,
        "hands_won": round_obj.hands_won,
        "scores": round_obj.scores,
    }


async def _get_scored_rounds(db: AsyncSession, game_id: int) -> list:
    """Fetch all scored rounds for a game, ordered by round_num."""
    result = await db.execute(
        select(Round)
        .where(Round.game_id == game_id, Round.status == "scored")
        .order_by(Round.round_num)
    )
    return result.scalars().all()


class ScoreboardService:
    @staticmethod
    async def get_scoreboard(db: AsyncSession, game_id: int, player_count: int = 0) -> dict:
        """Get cumulative scores and per-round breakdown."""
        scored_rounds = await _get_scored_rounds(db, game_id)
        rounds_data = [_round_to_dict(r) for r in scored_rounds]
        return compute_scoreboard(rounds_data, player_count)

    @staticmethod
    async def get_history(db: AsyncSession, game_id: int) -> list[dict]:
        """Get round-by-round bid vs actual vs score."""
        scored_rounds = await _get_scored_rounds(db, game_id)
        return [_round_to_dict(r) for r in scored_rounds]

    @staticmethod
    async def undo_last_round(db: AsyncSession, game) -> None:
        """Undo the last scored round — delete it and reset phase."""
        is_scoreboard = game.phase == "scoreboard"
        round_to_undo = game.current_round if is_scoreboard else game.current_round - 1
        if round_to_undo < 1:
            raise ValueError("No rounds to undo")

        await db.execute(
            delete(Round).where(Round.game_id == game.id, Round.round_num == round_to_undo)
        )
        game.current_round = 1 if round_to_undo == 1 else round_to_undo - 1
        game.phase = "bidding" if round_to_undo == 1 else "scoreboard"
        if game.status == "finished":
            game.status = "active"
            game.finished_at = None
        game.dealer_index = (game.dealer_index - 1) % len(game.players)
        await db.commit()
        await db.refresh(game)
