from pydantic import BaseModel, Field


class PlaygroundCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    pin: str = Field(..., min_length=4, max_length=4, pattern=r"^\d{4}$")
    players: list[str] = Field(..., min_length=1, max_length=8)


class PlaygroundAuth(BaseModel):
    name: str = Field(..., min_length=1)
    pin: str = Field(..., min_length=4, max_length=4)


class PlaygroundResponse(BaseModel):
    id: int
    name: str
    share_code: str
    players: list[str]

    model_config = {"from_attributes": True}
