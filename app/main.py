from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .models import ChallengeResponse, GuessRequest, GuessResponse
from .challenge import generate_challenge, challenges_store, clean_expired_challenges

app = FastAPI(title="Lichess Piece Guess API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/challenge", response_model=ChallengeResponse)
async def get_challenge(difficulty: str = "medium"):
    if difficulty not in ["easy", "medium", "hard"]:
        difficulty = "medium"
    try:
        challenge = await generate_challenge(difficulty)
        return ChallengeResponse(
            challenge_id=challenge.challenge_id,
            fen=challenge.fen,
            hidden_squares=challenge.hidden_squares,
            game=challenge.game
        )
    except Exception as e:
        import logging
        logging.error(f"Error generating challenge: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Failed to fetch challenge from Lichess")

@app.post("/api/challenge/{challenge_id}/guess", response_model=GuessResponse)
def submit_guess(challenge_id: str, request: GuessRequest):
    clean_expired_challenges()
    challenge = challenges_store.get(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found or expired")
        
    score = 0
    results = {}
    for sq, correct_piece in challenge.answers.items():
        user_guess = request.answers.get(sq)
        is_correct = (user_guess == correct_piece)
        results[sq] = is_correct
        if is_correct:
            score += 1
            
    # Clean up since it's answered
    del challenges_store[challenge_id]
            
    return GuessResponse(
        score=score,
        total=len(challenge.answers),
        results=results,
        answers=challenge.answers,
        game=challenge.game
    )

@app.get("/api/challenge/{challenge_id}")
def get_challenge_status(challenge_id: str):
    challenge = challenges_store.get(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return {
        "challenge_id": challenge.challenge_id,
        "fen": challenge.fen,
        "game": challenge.game
    }
