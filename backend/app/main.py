from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
from typing import Dict
from copy import deepcopy
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from .config import settings
from .database import init_db, get_db
from .db_models import DailyGuess, DailyChallenge
from .challenge import get_or_create_daily_gauntlet
from .move_puzzle import generate_move_puzzle, store_puzzle_answer, get_puzzle_answer
from .lichess import lichess_client

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await lichess_client.close()

app = FastAPI(title="Chess Piece Guess API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_today_str() -> str:
    # Use UTC date as the standard "today"
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/api/daily/today")
async def get_daily_gauntlet(db: AsyncSession = Depends(get_db)):
    date_str = get_today_str()
    try:
        puzzles = await get_or_create_daily_gauntlet(db, date_str)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch/generate daily challenge")
        
    # DO NOT leak answers to frontend!
    safe_puzzles = deepcopy(puzzles)
    for p in safe_puzzles:
        p.pop("answers", None)
        
    return {
        "date": date_str,
        "gauntlet": safe_puzzles
    }

@app.post("/api/daily/today/guess/{level}")
async def submit_daily_guess(level: int, user_answers: Dict[str, str], request: Request, db: AsyncSession = Depends(get_db)):
    if level < 1 or level > 4:
        raise HTTPException(status_code=400, detail="Level must be between 1 and 4")

    if len(user_answers) > 64:
        raise HTTPException(status_code=400, detail="Too many answer keys provided")

    date_str = get_today_str()
    
    # 1. Fetch from DB
    result = await db.execute(select(DailyChallenge).where(DailyChallenge.date_id == date_str))
    db_challenge = result.scalars().first()
    
    if not db_challenge:
        raise HTTPException(status_code=404, detail="Daily challenge not initialized")
        
    puzzles = db_challenge.puzzles
    puzzle = next((p for p in puzzles if p["level"] == level), None)
    
    if not puzzle:
        raise HTTPException(status_code=404, detail="Level not found in daily gauntlet")
        
    answers = puzzle["answers"]
    
    # 2. Evaluate score
    score = 0
    results = {}
    for sq, p in answers.items():
        correct = (user_answers.get(sq) == p)
        results[sq] = correct
        if correct: score += 1
        
    # 3. Hash IP
    ip = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()
    
    # 4. Save to DB asynchronously
    existing = await db.execute(select(DailyGuess).where(
        DailyGuess.date_id == date_str,
        DailyGuess.level_id == level,
        DailyGuess.ip_hash == ip_hash
    ))
    has_guessed = existing.scalars().first()
    
    if has_guessed:
        # Return previously recorded score to keep client and database distribution in sync
        return {
            "score": has_guessed.score,
            "max_score": level,
            "results": results,
            "actual_answers": answers,
            "already_submitted": True,
        }

    new_guess = DailyGuess(date_id=date_str, level_id=level, ip_hash=ip_hash, score=score)
    db.add(new_guess)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
    
    # 5. Return basic results
    return {
        "score": score,
        "max_score": level,
        "results": results,
        "actual_answers": answers
    }

@app.get("/api/daily/today/stats")
async def get_daily_stats(request: Request, db: AsyncSession = Depends(get_db)):
    date_str = get_today_str()
    ip_hash = hashlib.sha256((request.client.host if request.client else "unknown").encode()).hexdigest()
    
    # User's total score
    user_records = await db.execute(
        select(DailyGuess.score).where(
            DailyGuess.date_id == date_str, 
            DailyGuess.ip_hash == ip_hash
        )
    )
    user_scores = user_records.scalars().all()
    user_total = sum(user_scores)
    
    # Global distribution query utilizing PostgreSQL capabilities
    # Find all users who completed the gauntlet (exactly 4 levels guessed today)
    query = text("""
        SELECT sum_score, COUNT(*) as count 
        FROM (
            SELECT ip_hash, SUM(score) as sum_score 
            FROM daily_guesses 
            WHERE date_id = :date 
            GROUP BY ip_hash 
            HAVING COUNT(level_id) = 4
        ) AS subq 
        GROUP BY sum_score
    """)
    result = await db.execute(query, {"date": date_str})
    
    distribution = {i: 0 for i in range(11)} # 0 to 10
    total_players = 0
    for row in result:
        val = int(row[0])
        cnt = int(row[1])
        distribution[val] = cnt
        total_players += cnt
        
    return {
        "user_total": user_total,
        "total_players": total_players,
        "distribution": distribution
    }

# ---------------------------------------------------------------------------
# Guess the Move endpoints
# ---------------------------------------------------------------------------

@app.get("/api/move-guess/puzzle")
async def get_move_puzzle(db: AsyncSession = Depends(get_db)):
    try:
        puzzle = await generate_move_puzzle()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate move puzzle")

    # Store correct answer server-side
    await store_puzzle_answer(db, puzzle["puzzle_id"], puzzle["correct_move"], puzzle["game_info"])

    # Return puzzle WITHOUT the correct answer
    return {
        "puzzle_id": puzzle["puzzle_id"],
        "fen": puzzle["fen"],
        "side_to_move": puzzle["side_to_move"],
        "move_a": puzzle["move_a"],
        "move_b": puzzle["move_b"],
    }

@app.post("/api/move-guess/answer/{puzzle_id}")
async def submit_move_answer(puzzle_id: str, body: Dict[str, str], db: AsyncSession = Depends(get_db)):
    chosen = body.get("chosen_move")
    if not chosen:
        raise HTTPException(status_code=400, detail="Missing 'chosen_move' field")

    answer_data = await get_puzzle_answer(db, puzzle_id)
    if answer_data is None:
        raise HTTPException(status_code=404, detail="Puzzle expired or not found")

    correct_move = answer_data["correct_move"]
    is_correct = chosen == correct_move

    return {
        "correct": is_correct,
        "correct_move": correct_move,
        "chosen_move": chosen,
        "game_info": answer_data.get("game_info"),
    }
