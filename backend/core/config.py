from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    mongodb_url: str = "mongodb://localhost:27017/tradingagents"
    redis_url: str = "redis://localhost:6379"

    # Security
    secret_key: str = "your-super-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Application
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()