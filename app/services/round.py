"""Round service — bid submission, hands entry, scoring, phase enforcement."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.round import Round
from app.services.scoring import calculate_round_scores
from app.utils.trump import get_cards_for_round, get_trump_for_round


class RoundService:

    @staticmethod
    async def create_round(db: AsyncSession, game) -> Round:
        cards_dealt = get_cards_for_round(game.current_round)
        trump_suit = get_trump_for_round(game.current_round)

        round_obj = Round(
            game_id=game.id,
            round_num=game.current_round,
            cards_dealt=cards_dealt,
            trump_suit=trump_suit,
        )
        db.add(round_obj)
        await db.commit()
        await db.refresh(round_obj)
        return round_obj

    @staticmethod
    async def get_current_round(db: AsyncSession, game_id: int, round_num: int) -> Round | None:
        result = await db.execute(
            select(Round).where(
                Round.game_id == game_id,
                Round.round_num == round_num,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def submit_bid(
        db: AsyncSession,
        round_obj: Round,
        player_index: int,
        value: int,
        must_lose: bool = False,
        cards_dealt: int = 0,
        player_count: int = 0,
    ) -> None:
        if round_obj.status != "bidding":
            raise ValueError(f"Round is not in bidding phase (current: {round_obj.status})")

        player_key = str(player_index)
        if player_key in round_obj.bids:
            raise ValueError(f"Bid already submitted for player {player_index}")

        if must_lose:
            bids_so_far = len(round_obj.bids)
            is_last_player = bids_so_far == player_count - 1
            if is_last_player:
                existing_total = sum(round_obj.bids.values())
                if existing_total + value == cards_dealt:
                    raise ValueError(
                        f"Bid {value} rejected: must-lose mode — "
                        f"total bids ({existing_total + value}) "
                        f"cannot equal cards dealt ({cards_dealt})"
                    )

        # SQLAlchemy needs a new dict to detect JSONB mutation
        updated_bids = {**round_obj.bids, player_key: value}
        round_obj.bids = updated_bids
        await db.commit()
        await db.refresh(round_obj)

    @staticmethod
    async def edit_bid(
        db: AsyncSession,
        round_obj: Round,
        player_index: int,
        value: int,
    ) -> None:
        player_key = str(player_index)
        if player_key not in round_obj.bids:
            raise ValueError(f"No bid exists for player {player_index}")

        updated_bids = {**round_obj.bids, player_key: value}
        round_obj.bids = updated_bids
        await db.commit()
        await db.refresh(round_obj)

    @staticmethod
    async def confirm_bids(
        db: AsyncSession,
        round_obj: Round,
        player_count: int,
    ) -> None:
        if len(round_obj.bids) < player_count:
            missing = player_count - len(round_obj.bids)
            raise ValueError(f"{missing} player(s) still missing bids")

        round_obj.status = "playing"
        await db.commit()
        await db.refresh(round_obj)

    @staticmethod
    async def submit_hands(
        db: AsyncSession,
        round_obj: Round,
        player_index: int,
        value: int,
    ) -> None:
        if round_obj.status != "round_end":
            raise ValueError(f"Round is not in round_end phase (current: {round_obj.status})")

        player_key = str(player_index)
        updated_hands = {**round_obj.hands_won, player_key: value}
        round_obj.hands_won = updated_hands
        await db.commit()
        await db.refresh(round_obj)

    @staticmethod
    async def end_round(
        db: AsyncSession,
        round_obj: Round,
        player_count: int,
        formula: str,
    ) -> dict[str, int]:
        if len(round_obj.hands_won) < player_count:
            missing = player_count - len(round_obj.hands_won)
            raise ValueError(f"{missing} player(s) still missing hands_won entry")

        scores = calculate_round_scores(round_obj.bids, round_obj.hands_won, formula)
        round_obj.scores = scores
        round_obj.status = "scored"
        await db.commit()
        await db.refresh(round_obj)
        return scores
