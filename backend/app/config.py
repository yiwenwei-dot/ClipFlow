from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    DATABASE_URL: str = "sqlite+aiosqlite:///./clipflow.db"
    STORAGE_PATH: str = "./storage"

    DEEPGRAM_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    FFMPEG_PATH: str = "ffmpeg"
    FFPROBE_PATH: str = "ffprobe"

    MAX_UPLOAD_SIZE_MB: int = 2048

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
