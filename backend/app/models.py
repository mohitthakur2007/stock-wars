from pydantic import BaseModel, Field


class CreateRoomRequest(BaseModel):
    host_name: str = Field(min_length=2, max_length=20)
    max_players: int = Field(default=8, ge=2, le=8)
    starting_cash: int = Field(default=10000, ge=5000, le=20000)
    company_count: int = Field(default=12, ge=10, le=15)


class JoinRoomRequest(BaseModel):
    player_name: str = Field(min_length=2, max_length=20)


class ReadyRequest(BaseModel):
    ready: bool


class StartGameRequest(BaseModel):
    host_token: str


class BidRequest(BaseModel):
    player_id: str
    amount: int = Field(gt=0)