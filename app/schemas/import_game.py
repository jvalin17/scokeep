"""Pydantic schemas for the game import endpoint."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

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

    @model_validator(mode="after")
    def validate_round_data(self):
        if self.finished_at < self.started_at:
            raise ValueError("finished_at must be >= started_at")
        round_nums = [r.round_num for r in self.rounds]
        if len(round_nums) != len(set(round_nums)):
            raise ValueError("Duplicate round_num values")
        valid_keys = {str(i) for i in range(len(self.players))}
        for round_data in self.rounds:
            if set(round_data.bids.keys()) != valid_keys:
                raise ValueError(
                    f"Round {round_data.round_num}: bids keys must be {valid_keys}"
                )
            if set(round_data.hands_won.keys()) != valid_keys:
                raise ValueError(
                    f"Round {round_data.round_num}: hands_won keys must be {valid_keys}"
                )
            for bid in round_data.bids.values():
                if bid < 0 or bid > round_data.cards_dealt:
                    max_bid = round_data.cards_dealt
                    raise ValueError(
                        f"Round {round_data.round_num}: bid {bid} out of range 0..{max_bid}"
                    )
            for hands in round_data.hands_won.values():
                if hands < 0:
                    raise ValueError(
                        f"Round {round_data.round_num}: hands_won cannot be negative"
                    )
            if sum(round_data.hands_won.values()) > round_data.cards_dealt:
                raise ValueError(
                    f"Round {round_data.round_num}: hands_won sum exceeds cards_dealt"
                )
        return self


class ImportGameResponse(BaseModel):
    game_id: int
    rounds_imported: int
    already_existed: bool = False
