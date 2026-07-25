"""Round request/response schemas."""

from pydantic import BaseModel, Field


class BidSubmit(BaseModel):
    player_index: int = Field(..., ge=0, le=7)
    value: int = Field(..., ge=0, le=8)


class BidEdit(BaseModel):
    value: int = Field(..., ge=0, le=8)


class HandsSubmit(BaseModel):
    player_index: int = Field(..., ge=0, le=7)
    value: int = Field(..., ge=0, le=8)


class RoundResponse(BaseModel):
    id: int
    game_id: int
    round_num: int
    cards_dealt: int
    trump_suit: str
    bids: dict
    hands_won: dict
    scores: dict
    status: str

    model_config = {"from_attributes": True}
