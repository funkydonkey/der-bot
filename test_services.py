"""Test script to verify service connections."""
import asyncio
import sys

from config.logging_config import setup_logging
from config.settings import settings
from database.database import init_database, close_database
from services.openai_service import init_openai, test_openai_connection
from services.ocr_service import init_ocr_client, test_ocr_connection, close_ocr_client


async def test_all_services():
    """Test all service connections."""
    setup_logging()

    print("=" * 60)
    print("Testing Service Connections")
    print("=" * 60)

    # Test 1: Database
    print("\n1. Testing Database Connection...")
    try:
        await init_database()
        print("   ✓ Database connection successful")
    except Exception as e:
        print(f"   ✗ Database connection failed: {e}")
        return False

    # Test 2: OpenAI
    print("\n2. Testing OpenAI API Connection...")
    try:
        init_openai()
        await test_openai_connection()
        print("   ✓ OpenAI API connection successful")
    except Exception as e:
        print(f"   ✗ OpenAI API connection failed: {e}")
        return False

    # Test 3: MCP OCR (non-blocking)
    print("\n3. Testing MCP OCR Server Connection...")
    try:
        init_ocr_client()
        await test_ocr_connection()
        print("   ✓ MCP OCR server connection successful")
    except Exception as e:
        print(f"   ⚠ MCP OCR server test failed (non-blocking): {e}")

    # Test 4: Telegram Bot Token Format
    print("\n4. Validating Telegram Bot Token...")
    token = settings.telegram_bot_token
    if token and token != "your_telegram_bot_token_here":
        if ":" in token:
            print("   ✓ Telegram bot token format looks valid")
        else:
            print("   ⚠ Telegram bot token format may be invalid (should contain ':')")
    else:
        print("   ⚠ Telegram bot token not set (update .env file)")

    # Cleanup
    await close_database()
    await close_ocr_client()

    print("\n" + "=" * 60)
    print("Service Connection Tests Completed")
    print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_all_services())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
