"""Game service — create, retrieve, advance rounds, end game.

Game-type behavior is owned by Rule Packs (`app.services.packs`).
"""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ACTIVE_GAME_TTL_MINUTES, DEFAULT_ROUNDS_PER_SET
from app.models.game import Game
from app.services.packs.registry import (
    OPEN_ENDED_ROUND_CAP_STEP as SCORESHEET_OPEN_ENDED_ROUNDS,
)
from app.services.packs.registry import get_pack, get_pack_for_settings, is_scoresheet_settings
from app.utils.sanitize import sanitize_player_names

ROUNDS_PER_SET = DEFAULT_ROUNDS_PER_SET


class GameService:
    @staticmethod
    def game_type_is_locked(*, completed_rounds: int) -> bool:
        """Lock game_type after the first scored round (immutable mid-session)."""
        return completed_rounds >= 1

    @staticmethod
    async def create(
        db: AsyncSession,
        playground_id: int,
        players: list[str],
        settings: dict,
    ) -> Game:
        pack = get_pack((settings or {}).get("game_type"))
        merged_settings = pack.merge_settings(settings or {})
        total_rounds = pack.initial_total_rounds(merged_settings)

        game = Game(
            playground_id=playground_id,
            players=sanitize_player_names(players),
            settings=merged_settings,
            total_rounds=total_rounds,
            phase=pack.start_phase,
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
        """Return active game only if updated within TTL."""
        cutoff = datetime.now(tz=None) - timedelta(minutes=ACTIVE_GAME_TTL_MINUTES)  # noqa: DTZ005
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
        pack = get_pack_for_settings(game.settings)
        pack.grow_total_rounds_if_needed(game)

        # Judgement: at last completed round, enter review without incrementing.
        if pack.id == "kachuful" and game.current_round >= game.total_rounds:
            game.phase = "review"
            await db.commit()
            await db.refresh(game)
            return

        player_count = len(game.players)
        game.current_round += 1
        game.dealer_index = (game.dealer_index + 1) % player_count
        game.phase = pack.next_phase_on_advance(game)

        await db.commit()
        await db.refresh(game)

    @staticmethod
    async def extend_game(db: AsyncSession, game: Game) -> None:
        """Add another set — Judgement only. Open-ended packs raise ValueError."""
        pack = get_pack_for_settings(game.settings)
        if not pack.supports_extend:
            raise ValueError(f"{pack.display_name} games do not support extend")

        rounds_per_set = game.settings.get("rounds_per_set", ROUNDS_PER_SET)
        game.total_rounds += rounds_per_set
        num_sets = game.settings.get("num_sets", 3) + 1
        game.settings = {**game.settings, "num_sets": num_sets}
        await db.commit()
        await db.refresh(game)

    @staticmethod
    async def end_game(db: AsyncSession, game: Game) -> None:
        game.phase = "review"
        await db.commit()
        await db.refresh(game)

    @staticmethod
    async def confirm_final(db: AsyncSession, game: Game) -> None:
        """Finalize game from review phase — lock scores; Judgement insights optional."""
        game.status = "finished"
        game.phase = "final"
        game.finished_at = func.now()
        await db.commit()
        await db.refresh(game)

        pack = get_pack_for_settings(game.settings)
        if pack.should_compute_judgement_insights:
            from app.services.insights import compute_insights

            await compute_insights(db, game.playground_id)

    @staticmethod
    async def update_phase(db: AsyncSession, game: Game, phase: str) -> None:
        pack = get_pack_for_settings(game.settings)
        if phase not in pack.allowed_phases:
            raise ValueError(f"Phase '{phase}' is not valid for {pack.display_name}")
        game.phase = phase
        await db.commit()
        await db.refresh(game)

    @staticmethod
    async def enter_review_rescore(db: AsyncSession, game: Game, round_num: int) -> None:
        """Reset a specific round for re-entry during review phase (Judgement)."""
        from app.services.round import RoundService

        round_obj = await RoundService.get_current_round(db, game.id, round_num)
        if not round_obj:
            raise ValueError(f"Round {round_num} not found")

        round_obj.scores = {}
        round_obj.status = "round_end"
        game.current_round = round_num
        game.phase = "round_end"
        game.settings = {**game.settings, "_review_rescore": True}
        await db.commit()
        await db.refresh(game)


__all__ = [
    "GameService",
    "ROUNDS_PER_SET",
    "SCORESHEET_OPEN_ENDED_ROUNDS",
    "is_scoresheet_settings",
]
