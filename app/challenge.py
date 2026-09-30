import chess
import chess.pgn
import io
import time
import secrets
import random
from typing import Dict, List, Tuple
from .models import InternalChallenge, GameInfo
from .lichess import lichess_client
from .config import settings

# In-memory store
challenges_store: Dict[str, InternalChallenge] = {}

def clean_expired_challenges():
    expired = [k for k, v in challenges_store.items() if v.is_expired()]
    for k in expired:
        del challenges_store[k]

def is_good_position(board: chess.Board) -> bool:
    if board.is_game_over():
        return False
    pieces = board.piece_map()
    if len(pieces) < 8: # require at least 8 pieces for a reasonable challenge
        return False
    # Ensure there are enough eligible pieces to hide. (non-kings)
    eligible = [sq for sq, p in pieces.items() if p.piece_type != chess.KING]
    if len(eligible) < 5:
        return False
    return True

def select_hidden_pieces(board: chess.Board, difficulty: str) -> Tuple[List[str], Dict[str, str]]:
    pieces = board.piece_map()
    
    # Filter candidates
    candidates = []
    for sq, p in pieces.items():
        if p.piece_type == chess.KING:
            continue
        if difficulty in ["easy", "medium"] and p.piece_type == chess.PAWN:
            # Maybe allow some pawns but prefer pieces? The requirements said:
            # Easy: prefer non-pawn pieces
            # Hard: allow pawns
            pass
            
        candidates.append(sq)
        
    random.shuffle(candidates)
    
    if difficulty == "easy":
        num_hide = random.randint(1, 2)
        # sort so pawns are at the end, so we prefer non-pawns
        candidates.sort(key=lambda sq: 1 if pieces[sq].piece_type == chess.PAWN else 0)
    elif difficulty == "medium":
        num_hide = random.randint(3, 4)
    elif difficulty == "hard":
        num_hide = random.randint(5, 7)
    else:
        num_hide = 3
        
    num_hide = min(num_hide, len(candidates))
    
    hidden_squares = candidates[:num_hide]
    
    answers = {}
    for sq in hidden_squares:
        sq_name = chess.square_name(sq)
        answers[sq_name] = pieces[sq].symbol()
        # Remove piece from board for the final FEN sent to user
        board.remove_piece_at(sq)
        
    hidden_square_names = [chess.square_name(sq) for sq in hidden_squares]
    return hidden_square_names, answers

async def generate_challenge(difficulty: str = "medium") -> InternalChallenge:
    clean_expired_challenges()
    
    for _ in range(5): # Retry loop
        pgn_text = await lichess_client.get_random_public_game()
        if not pgn_text:
            continue
            
        game = chess.pgn.read_game(io.StringIO(pgn_text))
        if not game:
            continue
            
        # Extract metadata
        variant = game.headers.get("Variant", "Standard")
        if variant != "Standard":
            continue
            
        game_id = game.headers.get("GameId", "unknown")
        site_url = game.headers.get("Site", f"https://lichess.org/{game_id}")
        white = game.headers.get("White", "Unknown")
        black = game.headers.get("Black", "Unknown")
        result = game.headers.get("Result", "*")
        
        # Traverse moves to find a good position
        board = game.board()
        positions = []
        node = game
        
        while node.variations:
            next_node = node.variation(0)
            board.push(next_node.move)
            if is_good_position(board):
                positions.append((board.copy(), board.ply()))
            node = next_node
            
        if not positions:
            continue
            
        # Pick a random valid position using weighted probability
        # We heavily weight later positions to bias toward midgame/endgame
        weights = [max(0.1, p[1] - 20) for p in positions]
        selected = random.choices(positions, weights=weights, k=1)[0]
        test_board, ply = selected
            
        # We have a good board. Hide pieces.
        hidden_squares, answers = select_hidden_pieces(test_board, difficulty)
        
        challenge_id = secrets.token_urlsafe(8)
        
        game_info = GameInfo(
            id=game_id,
            url=site_url,
            white=white,
            black=black,
            result=result,
            ply=ply
        )
        
        # FEN without the hidden pieces
        final_fen = test_board.fen()
        
        challenge = InternalChallenge(
            challenge_id=challenge_id,
            fen=final_fen,
            hidden_squares=hidden_squares,
            answers=answers,
            game=game_info,
            expires_at=time.time() + settings.challenge_expiry_seconds
        )
        
        challenges_store[challenge_id] = challenge
        return challenge
        
    raise Exception("Failed to generate a valid challenge after retries.")
