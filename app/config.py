from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    backend_cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    lichess_api_url: str = "https://lichess.org/api"
    lichess_export_url: str = "https://lichess.org/game/export"
    database_url: str = "postgresql+asyncpg://lichess_user:lichess_password@localhost:5432/lichess_piece_guess"
    minimum_pieces: int = 8
    minimum_moves: int = 25
    move_guess_min_elo: int = 2000
    move_guess_perf_types: list[str] = ["blitz", "rapid", "classical"]
    puzzle_ttl_seconds: int = 600

settings = Settings()
