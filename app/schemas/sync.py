"""Pydantic schemas for sync endpoints."""

from typing import Literal

from pydantic import BaseModel, Field


class SyncRoundRequest(BaseModel):
    round_num: int = Field(ge=1)
    cards_dealt: int = Field(ge=1, le=52)
    trump_suit: Literal["spades", "diamonds", "clubs", "hearts"]
    bids: dict[str, int]
    hands_won: dict[str, int]
    scores: dict[str, int]
    status: Literal["bidding", "playing", "round_end", "scored", "complete"]


class SyncGameStateRequest(BaseModel):
    phase: Literal["bidding", "playing", "round_end", "scoring", "scoreboard", "review", "final"]
    current_round: int = Field(ge=1)
    dealer_index: int = Field(ge=0)
    status: Literal["active", "finished"]
