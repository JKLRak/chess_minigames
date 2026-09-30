import httpx
import logging
import random
from typing import Optional
from .config import settings

logger = logging.getLogger(__name__)

class LichessClient:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "LichessPieceGuessApp/1.0 (Contact: local@example.com)"})
        self.cached_games: list[str] = []

    async def close(self):
        await self.client.aclose()

    async def get_random_tv_game_id(self) -> Optional[str]:
        try:
            resp = await self.client.get(f"{settings.lichess_api_url}/tv/channels")
            resp.raise_for_status()
            data = resp.json()
            
            # Filter for standard chess game channels only
            standard_keys = {"blitz", "rapid", "classical", "bullet", "bot"}
            channels = [v for k, v in data.items() if k in standard_keys]
            
            if not channels:
                return None
            channel = random.choice(channels)
            return channel.get("gameId")
        except Exception as e:
            logger.error(f"Failed to fetch TV channels: {e}")
            return None

    async def get_pgn(self, game_id: str) -> Optional[str]:
        try:
            resp = await self.client.get(f"{settings.lichess_export_url}/{game_id}?tags=true&clocks=false&evals=false&opening=false")
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            logger.error(f"Failed to fetch PGN for {game_id}: {e}")
            return None

    async def get_random_public_game(self) -> Optional[str]:
        if self.cached_games:
            return self.cached_games.pop(0)

        game_id = await self.get_random_tv_game_id()
        if not game_id:
            return None
            
        pgn = await self.get_pgn(game_id)
        if pgn:
            # Basic caching logic - could fetch multiple but since tv/channels returns ~10 we just fetch 1
            return pgn
        return None

lichess_client = LichessClient()
