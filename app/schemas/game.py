"""Game request/response schemas."""

from pydantic import BaseModel, Field


class GameSettings(BaseModel):
    game_type: str = Field(default="kachuful", pattern=r"^(kachuful|free)$")
    mode: str = Field(default="expert", pattern=r"^(expert|rookie|friendly)$")
    appearance: str = Field(default="standard", pattern=r"^(standard|interactive)$")
    timer_seconds: int = Field(default=3, ge=1, le=30)
    scoring_formula: str = Field(default="kachuful_standard")
    num_sets: int = Field(default=3, ge=1, le=10)
    must_lose: bool = Field(default=False)
    free_rounds: int = Field(default=10, ge=1, le=99)
    trump_rotation: list[str] = Field(
        default=["spades", "diamonds", "clubs", "hearts"]
    )


class GameCreate(BaseModel):
    playground_id: int
    players: list[str] = Field(..., min_length=2, max_length=8)
    settings: GameSettings = Field(default_factory=GameSettings)


class GameResponse(BaseModel):
    id: int
    playground_id: int
    players: list[str]
    settings: dict
    current_round: int
    total_rounds: int
    phase: str
    dealer_index: int
    status: str

    model_config = {"from_attributes": True}
