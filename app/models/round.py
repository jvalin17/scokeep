"""Round ORM model — one row per round per game."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Round(Base):
    __tablename__ = "round"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("game.id"), nullable=False
    )
    round_num: Mapped[int] = mapped_column(Integer, nullable=False)
    cards_dealt: Mapped[int] = mapped_column(Integer, nullable=False)
    trump_suit: Mapped[str] = mapped_column(String(10), nullable=False)
    bids: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    hands_won: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    scores: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="bidding"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("game_id", "round_num", name="uq_game_round"),
    )
