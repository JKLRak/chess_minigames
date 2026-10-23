import re
import httpx
import logging
import random
from typing import Optional
from .config import settings

logger = logging.getLogger(__name__)

class LichessClient:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "LichessPieceGuessApp/1.0 (Contact: local@example.com)"})
        self.cached_high_elo_games: list[str] = []

    async def close(self):
        await self.client.aclose()

    async def get_distinct_tv_game_ids(self, count: int = 4) -> list[str]:
        """Fetch distinct active TV game IDs across different channels."""
        try:
            resp = await self.client.get(f"{settings.lichess_api_url}/tv/channels")
            resp.raise_for_status()
            data = resp.json()

            standard_keys = ["blitz", "rapid", "classical", "bullet", "bot"]
            game_ids: list[str] = []
            for k in standard_keys:
                if k in data and data[k].get("gameId"):
                    gid = data[k]["gameId"]
                    if gid not in game_ids:
                        game_ids.append(gid)

            random.shuffle(game_ids)
            return game_ids[:count]
        except Exception as e:
            logger.error(f"Failed to fetch TV channels: {e}")
            return []

    async def get_random_tv_game_id(self) -> Optional[str]:
        game_ids = await self.get_distinct_tv_game_ids(count=1)
        return game_ids[0] if game_ids else None

    async def get_pgn(self, game_id: str) -> Optional[str]:
        try:
            resp = await self.client.get(f"{settings.lichess_export_url}/{game_id}?tags=true&clocks=false&evals=false&opening=false")
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            logger.error(f"Failed to fetch PGN for {game_id}: {e}")
            return None

    async def get_random_public_game(self, game_id: Optional[str] = None) -> Optional[str]:
        if not game_id:
            game_id = await self.get_random_tv_game_id()
        if not game_id:
            return None
            
        pgn = await self.get_pgn(game_id)
        if pgn:
            return pgn
        return None

    async def get_high_elo_game_pgn(self, min_elo: int = 2000) -> Optional[str]:
        """Fetch a PGN from a high-rated game by sampling a top player's recent games."""
        if self.cached_high_elo_games:
            return self.cached_high_elo_games.pop(0)

        perf_types = list(settings.move_guess_perf_types)
        random.shuffle(perf_types)

        for perf in perf_types:
            try:
                # 1. Grab top players from the leaderboard
                resp = await self.client.get(
                    f"{settings.lichess_api_url}/player/top/50/{perf}",
                    headers={"Accept": "application/vnd.lichess.v3+json"},
                )
                resp.raise_for_status()
                data = resp.json()
                users = data.get("users", [])
                if not users:
                    continue

                # Pick a random player
                random.shuffle(users)

                for user in users[:5]:
                    username = user.get("username") or user.get("id")
                    if not username:
                        continue

                    # 2. Fetch a small batch of their recent rated games as PGN
                    game_resp = await self.client.get(
                        f"{settings.lichess_api_url}/games/user/{username}",
                        params={
                            "rated": "true",
                            "perfType": perf,
                            "max": "5",
                        },
                        headers={"Accept": "application/x-chess-pgn"},
                    )
                    game_resp.raise_for_status()
                    pgn_text = game_resp.text.strip()
                    if not pgn_text:
                        continue

                    # The response may contain multiple games separated by double newlines
                    games = [g.strip() for g in pgn_text.split("\n\n\n") if g.strip()]
                    random.shuffle(games)

                    valid_games = [g for g in games if _both_players_above_elo(g, min_elo)]
                    if valid_games:
                        selected = valid_games.pop(0)
                        # Cache remaining games (cap at 20 games)
                        if len(self.cached_high_elo_games) < 20:
                            self.cached_high_elo_games.extend(valid_games)
                        return selected

            except Exception as e:
                logger.warning(f"Failed to fetch high-elo game for perf={perf}: {e}")
                continue

        logger.error("Exhausted all perf types without finding a suitable high-elo game")
        return None


def _both_players_above_elo(pgn_text: str, min_elo: int) -> bool:
    """Quick check that both WhiteElo and BlackElo headers are above the threshold."""
    white_elo = _extract_header(pgn_text, "WhiteElo")
    black_elo = _extract_header(pgn_text, "BlackElo")
    if white_elo is None or black_elo is None:
        return False
    return white_elo >= min_elo and black_elo >= min_elo


def _extract_header(pgn_text: str, header_name: str) -> Optional[int]:
    """Extract an integer header value from raw PGN text."""
    pattern = rf'\[{header_name}\s+"(\d+)"\]'
    match = re.search(pattern, pgn_text)
    if match:
        return int(match.group(1))
    return None


lichess_client = LichessClient()
