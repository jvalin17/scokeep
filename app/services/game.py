"""Game service — create, retrieve, advance rounds, end game."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.utils.sanitize import sanitize_player_names
from app.utils.trump import ROUNDS_PER_SET

DEFAULT_NUM_SETS = 3

DEFAULT_SETTINGS = {
    "game_type": "kachuful",
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
        rounds_per_set = merged_settings.get("rounds_per_set", ROUNDS_PER_SET)
        total_rounds = num_sets * rounds_per_set

        game = Game(
            playground_id=playground_id,
            players=sanitize_player_names(players),
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
    async def get_active_for_playground(db: AsyncSession, playground_id: int) -> Game | None:
        """Return active game only if updated within the last 10 minutes."""
        cutoff = datetime.now(tz=None) - timedelta(minutes=30)  # noqa: DTZ005
        result = await db.execute(
            select(Game)
            .where(
                Game.playground_id == playground_id,
                Game.status == "active",
                Game.updated_at > cutoff,
            )
            .order_by(Game.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def advance_round(db: AsyncSession, game: Game) -> None:
        if game.current_round >= game.total_rounds:
            game.status = "finished"
            game.phase = "final"
            game.finished_at = func.now()
        else:
            player_count = len(game.players)
            game.current_round += 1
            game.dealer_index = (game.dealer_index + 1) % player_count
            game.phase = "bidding"

        await db.commit()
        await db.refresh(game)

    @staticmethod
    async def extend_game(db: AsyncSession, game: Game) -> None:
        """Add another set to the game."""
        rounds_per_set = game.settings.get("rounds_per_set", ROUNDS_PER_SET)
        game.total_rounds += rounds_per_set
        num_sets = game.settings.get("num_sets", 3) + 1
        game.settings = {**game.settings, "num_sets": num_sets}
        await db.commit()
        await db.refresh(game)

    @staticmethod
    async def end_game(db: AsyncSession, game: Game) -> None:
        game.status = "finished"
        game.phase = "final"
        game.finished_at = func.now()
        await db.commit()
        await db.refresh(game)

    @staticmethod
    async def update_phase(db: AsyncSession, game: Game, phase: str) -> None:
        game.phase = phase
        await db.commit()
        await db.refresh(game)
