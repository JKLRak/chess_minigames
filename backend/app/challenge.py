import asyncio
import chess
import chess.pgn
import io
import random
import logging
from typing import Dict, List, Tuple, TypedDict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .lichess import lichess_client
from .db_models import DailyChallenge

from .config import settings

MINIMUM_PIECES = settings.minimum_pieces
MINIMUM_MOVES = settings.minimum_moves
logger = logging.getLogger(__name__)

class GameInfoDict(TypedDict):
    id: str
    url: str
    white: str
    black: str
    result: str
    ply: int

class PuzzleDict(TypedDict):
    level: int
    fen: str
    hidden_squares: List[str]
    answers: Dict[str, str]
    game_info: GameInfoDict

def is_good_position(board: chess.Board) -> bool:
    if board.is_game_over():
        return False
    pieces = board.piece_map()
    return len(pieces) >= MINIMUM_PIECES

def select_hidden_pieces(board: chess.Board, num_hide: int) -> Tuple[List[str], Dict[str, str]]:
    pieces = board.piece_map()
    candidates = []
    
    for sq, p in pieces.items():
        if p.piece_type != chess.KING:
            candidates.append(sq)
        
    random.shuffle(candidates)
            
    hidden_squares = candidates[:num_hide]
    hidden_names = []
    answers = {}
    
    for sq in hidden_squares:
        sq_name = chess.square_name(sq)
        hidden_names.append(sq_name)
        answers[sq_name] = pieces[sq].symbol()
        board.remove_piece_at(sq)
        
    # Explicit intent mathematically preserves FEN safety visually correctly
    board.castling_rights = 0
    board.ep_square = None
    
    return hidden_names, answers

async def generate_single_puzzle(level: int, game_id: Optional[str] = None) -> PuzzleDict:
    for _ in range(5):
        try:
            pgn_text = await lichess_client.get_random_public_game(game_id=game_id)
            if not pgn_text: continue
                
            game = chess.pgn.read_game(io.StringIO(pgn_text))
            # Protect against empty parsed games and internal parse errors from incomplete HTTP streams
            if not game or game.errors:
                continue
                
            variant = game.headers.get("Variant", "Standard")
            if variant != "Standard":
                continue
                
            site_url = game.headers.get("Site", "https://lichess.org")
            game_id = site_url.split("/")[-1] if "/" in site_url else "unknown"
            
            moves = list(game.mainline_moves())
            if len(moves) < MINIMUM_MOVES:
                continue
                
            eligible_plies = range(20, len(moves))
            weights = [max(0.1, ply - 20) for ply in eligible_plies]
            
            target_ply = random.choices(eligible_plies, weights=weights, k=1)[0]
            
            board = game.board()
            for move in moves[:target_ply]:
                board.push(move)
                
            if not is_good_position(board):
                continue
            
            hidden_squares, answers = select_hidden_pieces(board, level)
            
            # Mappings for type safety dictionary matches
            return {
                "level": level,
                "fen": board.fen(),
                "hidden_squares": hidden_squares,
                "answers": answers,
                "game_info": {
                    "id": game_id,
                    "url": site_url,
                    "white": game.headers.get("White", "Unknown"),
                    "black": game.headers.get("Black", "Unknown"),
                    "result": game.headers.get("Result", "*"),
                    "ply": target_ply
                }
            }
        except Exception as e:
            logger.warning(f"Error evaluating candidate puzzle block: {e}")
            
    raise Exception(f"Failed to cleanly construct isolated validation challenge mechanics for tier #{level}")

async def get_or_create_daily_gauntlet(db: AsyncSession, date_str: str) -> List[PuzzleDict]:
    # Cached Hit Protocol Resolution
    result = await db.execute(select(DailyChallenge).where(DailyChallenge.date_id == date_str))
    db_challenge = result.scalars().first()
    
    if db_challenge:
        return db_challenge.puzzles
        
    logger.info(f"Dynamically generating concurrent infrastructure arrays for {date_str}...")
    
    # Draw distinct active games across different channels to ensure variety
    distinct_game_ids = await lichess_client.get_distinct_tv_game_ids(count=4)
    while len(distinct_game_ids) < 4:
        distinct_game_ids.append(None)
    
    # Sub-routines spawn entirely concurrently collapsing latency windows across 5 request bounds
    puzzles_tuple = await asyncio.gather(
        generate_single_puzzle(1, distinct_game_ids[0]),
        generate_single_puzzle(2, distinct_game_ids[1]),
        generate_single_puzzle(3, distinct_game_ids[2]),
        generate_single_puzzle(4, distinct_game_ids[3])
    )
        
    new_challenge = DailyChallenge(date_id=date_str, puzzles=list(puzzles_tuple))
    db.add(new_challenge)
    
    try:
        await db.commit()
    except IntegrityError:
        # A race condition occurred against a secondary asynchronous thread lock
        await db.rollback()
        result = await db.execute(select(DailyChallenge).where(DailyChallenge.date_id == date_str))
        db_challenge = result.scalars().first()
        if db_challenge:
            return db_challenge.puzzles
    
    return list(puzzles_tuple)
