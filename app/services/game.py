"""Game service — create, retrieve, advance rounds, end game."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.utils.trump import ROUNDS_PER_SET

DEFAULT_NUM_SETS = 3

DEFAULT_SETTINGS = {
    "mode": "expert",
    "appearance": "standard",
    "timer_seconds": 10,
    "scoring_formula": "kachuful_standard",
    "num_sets": DEFAULT_NUM_SETS,
    "must_lose": False,
    "trump_rotation": ["spades", "diamonds", "clubs", "hearts"],
}


class GameService:

    @staticmethod
    async def create(
        db: AsyncSession,
        playground_id: int,
        players: list[str],
        settings: dict,
    ) -> Game:
        merged_settings = {**DEFAULT_SETTINGS, **settings}
        num_sets = merged_settings["num_sets"]
        total_rounds = num_sets * ROUNDS_PER_SET

        game = Game(
            playground_id=playground_id,
            players=players,
            settings=merged_settings,
            total_rounds=total_rounds,
        )
        db.add(game)
        await db.commit()
        await db.refresh(game)
        return game

    @staticmethod
    async def get_by_id(db: AsyncSession, game_id: int) -> Game | None:
        result = await db.execute(select(Game).where(Game.id == game_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def advance_round(db: AsyncSession, game: Game) -> None:
        if game.current_round >= game.total_rounds:
            game.status = "finished"
            game.phase = "final"
            game.finished_at = datetime.utcnow()
        else:
            player_count = len(game.players)
            game.current_round += 1
            game.dealer_index = (game.dealer_index + 1) % player_count
            game.phase = "bidding"

        await db.commit()
        await db.refresh(game)

    @staticmethod
    async def end_game(db: AsyncSession, game: Game) -> None:
        game.status = "finished"
        game.phase = "final"
        game.finished_at = datetime.utcnow()
        await db.commit()
        await db.refresh(game)

    @staticmethod
    async def update_phase(db: AsyncSession, game: Game, phase: str) -> None:
        game.phase = phase
        await db.commit()
        await db.refresh(game)
