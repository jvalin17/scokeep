"""Pydantic schemas for sync endpoints."""

from pydantic import BaseModel


class SyncRoundRequest(BaseModel):
    round_num: int
    cards_dealt: int
    trump_suit: str
    bids: dict[str, int]
    hands_won: dict[str, int]
    scores: dict[str, int]
    status: str


class SyncGameStateRequest(BaseModel):
    phase: str
    current_round: int
    dealer_index: int
    status: str
