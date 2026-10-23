# Chess Puzzles

A full-stack chess web application featuring missing piece deduction and master move prediction puzzles.

## Game Modes

- **Daily Gauntlet**: 4 progressive levels of missing piece deduction from active master games (hiding 1, 2, 3, and 4 pieces)
- **Guess the Move**: Endless streak challenge predicting moves played in 2000+ Elo rated games. Decoy moves are generated via heuristic without chess engine

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, PostgreSQL, SQLAlchemy 2.0 (async), asyncpg, python-chess, http
- **Frontend**: React 19, TypeScript, Vite, pure CSS with custom piece SVGs (tournament theme)

## Architecture Highlights

- **Fast Game Caching**: Batched game fetching serves move puzzles in ~16ms from memory without external API rate limits.
- **Multi-Worker Answer Storage**: Active puzzles and answers are stored in PostgreSQL with automatic TTL expiration, supporting multi-worker and containerized deployments.
- **Atomic Verification**: Puzzle answers are deleted immediately upon consumption to prevent answer replay or brute-forcing.

## Quickstart

### 1. Database
```bash
docker compose up -d
```

### 2. Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .  # or: uv sync
uvicorn app.main:app --port 8000 --reload
```
API documentation is available at `http://localhost:8000/docs`.

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

## License

MIT License. Chess piece vector assets designed by Colin M.L. Burnett (CC BY-SA 3.0).
