from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
from typing import Dict, Any
from copy import deepcopy
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from .config import settings
from .database import init_db, get_db
from .db_models import DailyGuess, DailyChallenge
from .challenge import get_or_create_daily_gauntlet

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Lichess Piece Guess API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Fine for early dev
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
    
    # 4. Save to DB asynchronously (upsert/ignore constraint is tricky, we check first)
    existing = await db.execute(select(DailyGuess).where(
        DailyGuess.date_id == date_str,
        DailyGuess.level_id == level,
        DailyGuess.ip_hash == ip_hash
    ))
    has_guessed = existing.scalars().first()
    
    if not has_guessed:
        new_guess = DailyGuess(date_id=date_str, level_id=level, ip_hash=ip_hash, score=score)
        db.add(new_guess)
        await db.commit()
    
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
    from sqlalchemy import text
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
