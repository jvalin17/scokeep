"""Pydantic schemas for the game import endpoint."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

PlayerName = Annotated[str, Field(min_length=1, max_length=50)]

VALID_TRUMP_SUITS = Literal["spades", "diamonds", "clubs", "hearts"]


class ImportRound(BaseModel):
    round_num: int = Field(ge=1)
    bids: dict[str, int]
    hands_won: dict[str, int]
    cards_dealt: int = Field(ge=1, le=26)
    trump_suit: VALID_TRUMP_SUITS
    scores: dict[str, int] | None = None  # optional — server re-derives


class ImportGameRequest(BaseModel):
    client_game_id: str = Field(min_length=5, max_length=50)
    started_at: datetime
    finished_at: datetime
    players: list[PlayerName] = Field(min_length=2, max_length=8)
    settings: dict[str, str | int | bool | float | list]
    rounds: list[ImportRound] = Field(min_length=1, max_length=100)


class ImportGameResponse(BaseModel):
    game_id: int
    rounds_imported: int
    already_existed: bool = False
