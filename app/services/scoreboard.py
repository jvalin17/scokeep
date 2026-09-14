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


class ScoreboardService:
    @staticmethod
    async def get_scoreboard(
        db: AsyncSession,
        game_id: int,
        player_count: int = 0,
    ) -> dict:
        """Get cumulative scores and per-round breakdown."""
        result = await db.execute(
            select(Round)
            .where(Round.game_id == game_id, Round.status == "scored")
            .order_by(Round.round_num)
        )
        scored_rounds = result.scalars().all()

        # Build totals from scored rounds
        totals: dict[str, int] = {}
        rounds_data = []

        for round_obj in scored_rounds:
            rounds_data.append(
                {
                    "round_num": round_obj.round_num,
                    "cards_dealt": round_obj.cards_dealt,
                    "trump_suit": round_obj.trump_suit,
                    "bids": round_obj.bids,
                    "hands_won": round_obj.hands_won,
                    "scores": round_obj.scores,
                }
            )
            for player_key, score in round_obj.scores.items():
                totals[player_key] = totals.get(player_key, 0) + score

        # Fill missing players with 0
        for i in range(player_count):
            totals.setdefault(str(i), 0)

        return {"totals": totals, "rounds": rounds_data}

    @staticmethod
    async def get_history(db: AsyncSession, game_id: int) -> list[dict]:
        """Get round-by-round bid vs actual vs score."""
        result = await db.execute(
            select(Round)
            .where(Round.game_id == game_id, Round.status == "scored")
            .order_by(Round.round_num)
        )
        scored_rounds = result.scalars().all()

        return [
            {
                "round_num": r.round_num,
                "cards_dealt": r.cards_dealt,
                "trump_suit": r.trump_suit,
                "bids": r.bids,
                "hands_won": r.hands_won,
                "scores": r.scores,
            }
            for r in scored_rounds
        ]

    @staticmethod
    async def undo_last_round(db: AsyncSession, game) -> None:
        """Undo the last scored round — delete it and reset to bidding."""
        # In scoreboard phase, current_round is the round just played
        # In bidding phase (after advance), current_round is the next round
        round_to_undo = game.current_round if game.phase == "scoreboard" else game.current_round - 1
        if round_to_undo < 1:
            raise ValueError("No rounds to undo")

        # Delete the round
        await db.execute(
            delete(Round).where(
                Round.game_id == game.id,
                Round.round_num == round_to_undo,
            )
        )

        if round_to_undo == 1:
            # Back to round 1 bidding, no dealer change
            game.current_round = 1
            game.phase = "bidding"
        else:
            # Go back to scoreboard of previous round
            game.current_round = round_to_undo - 1
            game.phase = "scoreboard"

        if game.status == "finished":
            game.status = "active"
            game.finished_at = None

        # Restore dealer index
        player_count = len(game.players)
        game.dealer_index = (game.dealer_index - 1) % player_count

        await db.commit()
        await db.refresh(game)
