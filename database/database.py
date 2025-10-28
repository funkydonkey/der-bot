"""Database connection and initialization."""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text

from config.settings import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

# Global engine and session maker
engine: Optional[AsyncEngine] = None
async_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


async def init_database() -> None:
    """Initialize database connection and create tables."""
    global engine, async_session_maker

    try:
        logger.info(f"Connecting to database: {settings.database_url.split('@')[-1] if '@' in settings.database_url else settings.database_url}")

        # Create async engine
        engine = create_async_engine(
            settings.database_url,
            echo=settings.app_env == "development",
            future=True,
        )

        # Create session maker
        async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Test connection
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))

        logger.info("✓ Database connection successful")

    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        raise


async def close_database() -> None:
    """Close database connection."""
    global engine

    if engine:
        await engine.dispose()
        logger.info("Database connection closed")


async def get_session() -> AsyncSession:
    """Get database session."""
    if async_session_maker is None:
        raise RuntimeError("Database not initialized")

    async with async_session_maker() as session:
        yield session
