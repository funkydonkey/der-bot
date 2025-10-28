"""Telegram message handlers."""
import logging

from aiogram import Router, types
from aiogram.filters import Command

logger = logging.getLogger(__name__)

# Create router
router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    """Handle /start command."""
    logger.info(f"Received /start command from user {message.from_user.id}")
    await message.answer("Message received")


@router.message()
async def handle_any_message(message: types.Message) -> None:
    """Handle any incoming message."""
    logger.info(
        f"Received message from user {message.from_user.id}: "
        f"type={message.content_type}, text={message.text[:50] if message.text else 'N/A'}"
    )
    await message.answer("Message received")
