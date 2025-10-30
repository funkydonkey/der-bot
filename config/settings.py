"""Application configuration settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_env: str = "development"
    log_level: str = "INFO"
    port: int = 10000  # Port for health check server (Render uses 10000 by default)

    # Telegram
    telegram_bot_token: str

    # OpenAI
    openai_api_key: str

    # OCR Service (optional - OCR.space)
    ocr_api_key: str = ""  # OCR.space API key (free tier available)
    ocr_api_endpoint: str = "https://api.ocr.space/parse/image"

    # Database (defaults to SQLite for local dev, override for production)
    database_url: str = "sqlite+aiosqlite:///./telegram_bot.db"


# Global settings instance
settings = Settings()
