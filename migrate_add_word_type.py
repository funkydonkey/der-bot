"""Database migration: Add word_type column to words table."""
import asyncio
import logging
from sqlalchemy import text

from database import database
from config.logging_config import setup_logging

logger = logging.getLogger(__name__)


async def migrate():
    """Add word_type column to existing words table."""
    setup_logging()

    logger.info("Starting database migration: Adding word_type column")

    # Initialize database connection
    await database.init_database()
    engine = database.engine

    async with engine.begin() as conn:
        # Try to add the column (will fail if it already exists)
        try:
            logger.info("Adding word_type column to words table...")
            alter_query = text("""
                ALTER TABLE words
                ADD COLUMN word_type VARCHAR(50)
            """)

            await conn.execute(alter_query)
            logger.info("✓ Successfully added word_type column")

            # Set default value for existing rows
            logger.info("Setting default word_type='other' for existing words...")
            update_query = text("""
                UPDATE words
                SET word_type = 'other'
                WHERE word_type IS NULL
            """)

            result = await conn.execute(update_query)
            logger.info(f"✓ Updated {result.rowcount} existing words")

        except Exception as e:
            error_msg = str(e).lower()
            if "duplicate column" in error_msg or "already exists" in error_msg:
                logger.info("✓ word_type column already exists, skipping migration")
            else:
                raise

    await database.close_database()
    logger.info("Migration completed successfully!")


if __name__ == "__main__":
    try:
        asyncio.run(migrate())
        print("\n✅ Migration successful! You can now restart the bot.")
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        print(f"\n❌ Migration failed: {e}")
        exit(1)
