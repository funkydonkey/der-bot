"""Main entry point for the Telegram bot."""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config.logging_config import setup_logging
from config.settings import settings
from database.database import init_database, close_database
from services.openai_service import init_openai, test_openai_connection
from services.ocr_service import init_ocr_client, test_ocr_connection, close_ocr_client
from services.health_server import start_health_server, stop_health_server
from handlers.vocabulary_handler import router as vocabulary_router
from handlers.message_handler import router as message_router

logger = logging.getLogger(__name__)


async def startup_checks() -> None:
    """Perform startup checks for all services."""
    logger.info("=" * 60)
    logger.info("Starting Telegram Bot - Performing Service Checks")
    logger.info("=" * 60)

    # Check 1: Database
    try:
        logger.info("Checking database connection...")
        await init_database()
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        sys.exit(1)

    # Check 2: OpenAI API
    try:
        logger.info("Checking OpenAI API connection...")
        init_openai()
        await test_openai_connection()
    except Exception as e:
        logger.error(f"OpenAI API check failed: {e}")
        sys.exit(1)

    # Check 3: MCP OCR Server (non-blocking)
    try:
        logger.info("Checking MCP OCR server connection...")
        init_ocr_client()
        await test_ocr_connection()
    except Exception as e:
        logger.warning(f"MCP OCR server check failed (non-blocking): {e}")
        # Don't exit - OCR is optional

    logger.info("=" * 60)
    logger.info("All critical service checks passed!")
    logger.info("=" * 60)


async def shutdown(dispatcher: Dispatcher, bot: Bot) -> None:
    """Graceful shutdown handler."""
    logger.info("Shutting down bot...")

    # Close all connections
    await close_database()
    await close_ocr_client()
    await stop_health_server()
    await bot.session.close()
    await dispatcher.storage.close()

    logger.info("Bot stopped successfully")


async def main() -> None:
    """Main function to start the bot."""
    # Setup logging
    setup_logging()

    # Perform startup checks
    await startup_checks()

    # Initialize bot and dispatcher with FSM storage
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher(storage=MemoryStorage())

    # Register routers (order matters - more specific first!)
    dp.include_router(vocabulary_router)  # Specific commands: /addword, /mywords, /quiz
    dp.include_router(message_router)     # Generic handlers: /start, /help, catch-all

    try:
        logger.info("✓ Telegram bot authorized successfully")

        # Start health check server (for Render.com port binding)
        await start_health_server(port=settings.port)

        logger.info("Bot is starting polling...")

        # Start polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

    except Exception as e:
        logger.error(f"Bot polling error: {e}")
        raise
    finally:
        await shutdown(dp, bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)