"""Pydantic schemas for sync endpoints."""

from typing import Literal

from pydantic import BaseModel, Field


class SyncRoundRequest(BaseModel):
    round_num: int = Field(ge=1)
    cards_dealt: int = Field(default=1, ge=0, le=52)
    trump_suit: str = Field(default="spades", max_length=10)
    bids: dict[str, int] = Field(default_factory=dict)
    hands_won: dict[str, int] = Field(default_factory=dict)
    scores: dict[str, int]
    status: Literal["bidding", "playing", "round_end", "scored", "complete", "active"] = "complete"


class SyncGameStateRequest(BaseModel):
    phase: Literal[
        "bidding",
        "playing",
        "round_end",
        "scoring",
        "scoreboard",
        "review",
        "final",
        "entry",
        "round_review",
        "intermission",
    ]
    current_round: int = Field(ge=1)
    dealer_index: int = Field(ge=0)
    status: Literal["active", "finished"]
