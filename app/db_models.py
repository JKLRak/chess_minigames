from sqlalchemy import Column, String, Integer, JSON, Float, UniqueConstraint
from .database import Base

class DailyChallenge(Base):
    __tablename__ = "daily_challenges"
    
    date_id = Column(String, primary_key=True, index=True) # e.g. "2026-09-30"
    puzzles = Column(JSON, nullable=False)
    # [ { "level": 1, "fen": "...", "hidden_squares": [...], "answers": {...}, "game_info": {...} }, ... ]

class DailyGuess(Base):
    __tablename__ = "daily_guesses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date_id = Column(String, index=True)
    level_id = Column(Integer, index=True)
    ip_hash = Column(String, index=True)
    score = Column(Integer)
    
    # Prevent the same IP from answering the same level on the same day twice for stats integrity
    __table_args__ = (
        UniqueConstraint('date_id', 'level_id', 'ip_hash', name='uq_daily_guess'),
    )

class MovePuzzleAnswer(Base):
    __tablename__ = "move_puzzle_answers"

    puzzle_id = Column(String, primary_key=True, index=True)
    correct_move = Column(String, nullable=False)
    game_info = Column(JSON, nullable=False)
    created_at = Column(Float, nullable=False, index=True)

