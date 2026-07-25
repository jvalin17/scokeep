"""Scoreboard service — cumulative scores, history, undo."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.round import Round


class ScoreboardService:

    @staticmethod
    async def get_scoreboard(
        db: AsyncSession, game_id: int, player_count: int = 0,
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
            rounds_data.append({
                "round_num": round_obj.round_num,
                "cards_dealt": round_obj.cards_dealt,
                "trump_suit": round_obj.trump_suit,
                "scores": round_obj.scores,
            })
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
        """Undo the last scored round — delete it and decrement game.current_round."""
        last_round_num = game.current_round - 1
        if last_round_num < 1:
            raise ValueError("No rounds to undo")

        # Delete the last round
        await db.execute(
            delete(Round).where(
                Round.game_id == game.id,
                Round.round_num == last_round_num,
            )
        )

        game.current_round = last_round_num
        game.phase = "bidding"
        if game.status == "finished":
            game.status = "active"
            game.finished_at = None

        # Restore dealer index
        player_count = len(game.players)
        game.dealer_index = (game.dealer_index - 1) % player_count

        await db.commit()
        await db.refresh(game)
