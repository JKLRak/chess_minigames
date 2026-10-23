"""
Guess-the-Move puzzle generation.

Given a high-Elo game, pick a mid-game position and present the real move
alongside a plausible-looking decoy.  Decoy selection uses lightweight
heuristics (no engine required) to keep the puzzle challenging.
"""

import time
import chess
import chess.pgn
import io
import random
import logging
import uuid
from typing import Optional, TypedDict, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from .lichess import lichess_client
from .config import settings
from .db_models import MovePuzzleAnswer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class MoveGameInfo(TypedDict):
    id: str
    url: str
    white: str
    black: str
    white_elo: int
    black_elo: int
    result: str
    ply: int

class MovePuzzle(TypedDict):
    puzzle_id: str
    fen: str
    side_to_move: str          # "white" | "black"
    move_a: str                # SAN notation
    move_b: str                # SAN notation
    correct_move: str          # SAN of the real move (stored server-side only)
    game_info: MoveGameInfo

# ---------------------------------------------------------------------------
# Decoy scoring
# ---------------------------------------------------------------------------

# Squares weighted by centrality (e4/d4/d5/e5 most valuable)
_CENTER = {chess.E4, chess.D4, chess.E5, chess.D5}
_EXTENDED_CENTER = {
    chess.C3, chess.D3, chess.E3, chess.F3,
    chess.C4, chess.F4,
    chess.C5, chess.F5,
    chess.C6, chess.D6, chess.E6, chess.F6,
}


def _score_decoy(board: chess.Board, move: chess.Move) -> float:
    """Assign a plausibility score to a potential decoy move (higher = better decoy)."""
    score = 0.0

    # Captures always look natural
    if board.is_capture(move):
        score += 3.0

    # Checks look intentional and purposeful
    board.push(move)
    gives_check = board.is_check()
    board.pop()
    if gives_check:
        score += 2.5

    # Prefer central destinations
    to_sq = move.to_square
    if to_sq in _CENTER:
        score += 2.0
    elif to_sq in _EXTENDED_CENTER:
        score += 1.0

    # Promotion moves look important
    if move.promotion:
        score += 2.0

    return score


def _is_hanging_after(board: chess.Board, move: chess.Move) -> bool:
    """Check if the moved piece is immediately attacked and undefended after the move."""
    board.push(move)
    to_sq = move.to_square
    piece = board.piece_at(to_sq)
    if piece is None:
        board.pop()
        return False

    attackers = board.attackers(not piece.color, to_sq)
    defenders = board.attackers(piece.color, to_sq)
    is_hanging = len(attackers) > 0 and len(defenders) == 0
    board.pop()
    return is_hanging


def _pick_decoy(board: chess.Board, real_move: chess.Move) -> Optional[chess.Move]:
    """Select a plausible decoy from legal moves, preferring same piece type and avoiding blunders."""
    real_piece = board.piece_at(real_move.from_square)
    candidates = []

    for move in board.legal_moves:
        if move == real_move:
            continue

        # Skip moves that leave the piece obviously hanging
        if _is_hanging_after(board, move):
            continue

        piece = board.piece_at(move.from_square)
        score = _score_decoy(board, move)

        # Strong bonus for same piece type — makes the puzzle harder
        if piece and real_piece and piece.piece_type == real_piece.piece_type:
            score += 4.0

        candidates.append((move, score))

    if not candidates:
        return None

    # Sort by score descending, pick randomly from top tier
    candidates.sort(key=lambda x: x[1], reverse=True)
    top_score = candidates[0][1]
    # Grab all candidates within 1.5 points of the top — provides variety
    top_tier = [m for m, s in candidates if s >= top_score - 1.5]

    return random.choice(top_tier)


# ---------------------------------------------------------------------------
# Puzzle generation
# ---------------------------------------------------------------------------

async def generate_move_puzzle() -> MovePuzzle:
    """Generate a single Guess-the-Move puzzle from a high-Elo game."""
    min_elo = settings.move_guess_min_elo

    for attempt in range(5):
        try:
            pgn_text = await lichess_client.get_high_elo_game_pgn(min_elo)
            if not pgn_text:
                logger.warning(f"Attempt {attempt+1}: no PGN returned")
                continue

            game = chess.pgn.read_game(io.StringIO(pgn_text))
            if not game or game.errors:
                continue

            variant = game.headers.get("Variant", "Standard")
            if variant != "Standard":
                continue

            moves = list(game.mainline_moves())
            if len(moves) < 30:
                continue

            # Pick a position in the middle of the game (20% to 80% of moves)
            low = max(10, int(len(moves) * 0.2))
            high = min(len(moves) - 1, int(len(moves) * 0.8))
            if low >= high:
                continue

            target_ply = random.randint(low, high)

            board = game.board()
            for move in moves[:target_ply]:
                board.push(move)

            real_move = moves[target_ply]

            # Must have enough legal moves for a meaningful choice
            legal_count = sum(1 for _ in board.legal_moves)
            if legal_count < 5:
                continue

            decoy = _pick_decoy(board, real_move)
            if decoy is None:
                continue

            real_san = board.san(real_move)
            decoy_san = board.san(decoy)

            # Shuffle the presentation order
            move_options = [real_san, decoy_san]
            random.shuffle(move_options)

            site_url = game.headers.get("Site", "https://lichess.org")
            game_id = site_url.split("/")[-1] if "/" in site_url else "unknown"

            white_elo = 0
            black_elo = 0
            try:
                white_elo = int(game.headers.get("WhiteElo", "0"))
                black_elo = int(game.headers.get("BlackElo", "0"))
            except ValueError:
                pass

            puzzle: MovePuzzle = {
                "puzzle_id": str(uuid.uuid4()),
                "fen": board.fen(),
                "side_to_move": "white" if board.turn == chess.WHITE else "black",
                "move_a": move_options[0],
                "move_b": move_options[1],
                "correct_move": real_san,
                "game_info": {
                    "id": game_id,
                    "url": site_url,
                    "white": game.headers.get("White", "Unknown"),
                    "black": game.headers.get("Black", "Unknown"),
                    "white_elo": white_elo,
                    "black_elo": black_elo,
                    "result": game.headers.get("Result", "*"),
                    "ply": target_ply,
                },
            }
            return puzzle

        except Exception as e:
            logger.warning(f"Move puzzle generation attempt {attempt+1} failed: {e}")

    raise Exception("Failed to generate move puzzle after 5 attempts")


# ---------------------------------------------------------------------------
# Server-side answer storage (PostgreSQL, multi-worker safe, TTL-based)
# ---------------------------------------------------------------------------

async def store_puzzle_answer(
    db: AsyncSession,
    puzzle_id: str,
    correct_move: str,
    game_info: Dict[str, Any],
) -> None:
    now = time.time()
    cutoff = now - settings.puzzle_ttl_seconds
    try:
        # Prune expired entries
        await db.execute(delete(MovePuzzleAnswer).where(MovePuzzleAnswer.created_at < cutoff))
        entry = MovePuzzleAnswer(
            puzzle_id=puzzle_id,
            correct_move=correct_move,
            game_info=game_info,
            created_at=now,
        )
        db.add(entry)
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to store move puzzle answer: {e}")
        await db.rollback()
        raise


async def get_puzzle_answer(db: AsyncSession, puzzle_id: str) -> Optional[Dict[str, Any]]:
    now = time.time()
    cutoff = now - settings.puzzle_ttl_seconds
    try:
        result = await db.execute(
            select(MovePuzzleAnswer).where(
                MovePuzzleAnswer.puzzle_id == puzzle_id,
                MovePuzzleAnswer.created_at >= cutoff,
            )
        )
        entry = result.scalars().first()
        if not entry:
            return None
        data = {
            "correct_move": entry.correct_move,
            "game_info": entry.game_info,
        }
        await db.delete(entry)
        await db.commit()
        return data
    except Exception as e:
        logger.error(f"Failed to get move puzzle answer: {e}")
        await db.rollback()
        return None
