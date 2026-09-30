from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    backend_cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    lichess_api_url: str = "https://lichess.org/api"
    lichess_export_url: str = "https://lichess.org/game/export"
    challenge_expiry_seconds: int = 1800 # 30 mins

settings = Settings()
