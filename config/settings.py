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

    # Telegram
    telegram_bot_token: str

    # OpenAI
    openai_api_key: str

    # MCP OCR Server (optional)
    mcp_ocr_endpoint: str = "https://mcp-ocr.example.com"

    # Database (defaults to SQLite for local dev, override for production)
    database_url: str = "sqlite+aiosqlite:///./telegram_bot.db"


# Global settings instance
settings = Settings()
