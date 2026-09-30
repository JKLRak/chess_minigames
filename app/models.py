from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import time

class GameInfo(BaseModel):
    id: str
    url: str
    white: str
    black: str
    result: Optional[str] = None
    ply: int

class ChallengeResponse(BaseModel):
    challenge_id: str
    fen: str
    hidden_squares: List[str]
    game: GameInfo

class GuessRequest(BaseModel):
    answers: Dict[str, str]

class GuessResponse(BaseModel):
    score: int
    total: int
    results: Dict[str, bool]
    answers: Dict[str, str]
    game: Optional[GameInfo] = None

class InternalChallenge(BaseModel):
    challenge_id: str
    fen: str
    hidden_squares: List[str]
    answers: Dict[str, str]
    game: GameInfo
    created_at: float = Field(default_factory=time.time)
    expires_at: float

    def is_expired(self) -> bool:
        return time.time() > self.expires_at
