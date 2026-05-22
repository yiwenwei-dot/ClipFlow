from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    DATABASE_URL: str = "sqlite+aiosqlite:///./clipflow.db"
    STORAGE_PATH: str = "./storage"

    # Optional API keys (no longer required - local models used by default)
    DEEPGRAM_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    HF_TOKEN: str = ""  # HuggingFace token for WhisperX diarization (free)

    # Local ML settings
    WHISPER_MODEL_SIZE: str = "base"  # tiny, base, small, medium, large-v3
    SIMILARITY_THRESHOLD: float = 0.78  # for duplicate detection

    FFMPEG_PATH: str = "ffmpeg"
    FFPROBE_PATH: str = "ffprobe"

    MAX_UPLOAD_SIZE_MB: int = 2048

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
