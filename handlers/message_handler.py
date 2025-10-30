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

    welcome_message = (
        f"👋 <b>Willkommen, {message.from_user.first_name}!</b>\n\n"
        f"🇩🇪 I'm your German vocabulary learning assistant!\n\n"
        f"<b>Available Commands:</b>\n"
        f"📝 /addword - Add a new German word\n"
        f"📋 /bulkadd - Add many words from text\n"
        f"📸 /addphoto - Add words from a photo\n"
        f"📚 /mywords - View your vocabulary\n"
        f"🎯 /quiz - Practice with a quiz\n"
        f"🗑️ /delete - Remove a word\n"
        f"ℹ️ /help - Show this help message\n\n"
        f"<i>Get started by adding your first word with /addword!</i>"
    )

    await message.answer(welcome_message, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    """Handle /help command."""
    help_message = (
        "<b>🇩🇪 German Vocabulary Bot Help</b>\n\n"
        "<b>Commands:</b>\n\n"
        "📝 <b>/addword</b>\n"
        "   Add a new German word to your vocabulary\n"
        "   Only the German word is needed - learn translation through quiz!\n\n"
        "📋 <b>/bulkadd</b>\n"
        "   Add many words at once by pasting text\n"
        "   Works with mixed languages, verb forms, and grammar notes\n"
        "   Perfect for importing from textbooks or personal notes\n\n"
        "📸 <b>/addphoto</b>\n"
        "   Add words from a photo or image\n"
        "   Take a picture of your textbook, notes, or any German text\n"
        "   Review and confirm extracted words before saving\n\n"
        "📚 <b>/mywords</b>\n"
        "   View all your saved words with statistics\n\n"
        "🎯 <b>/quiz</b>\n"
        "   Practice with a random word from your vocabulary\n"
        "   First attempt will save the correct translation\n\n"
        "🗑️ <b>/delete</b> <i>&lt;word&gt;</i>\n"
        "   Remove a word from your vocabulary\n"
        "   Example: /delete hund or /delete der Hund\n\n"
        "<b>Features:</b>\n"
        "✨ Automatic article detection (der/die/das)\n"
        "🤖 AI-powered translation validation\n"
        "📊 Track your learning progress\n"
        "💬 Instant feedback on your answers\n"
        "🖼️ OCR text extraction from images\n"
        "📋 Bulk import from pasted text\n\n"
        "<i>Need help? Contact support or check the docs!</i>"
    )

    await message.answer(help_message, parse_mode="HTML")


@router.message()
async def handle_any_message(message: types.Message) -> None:
    """Handle any incoming message outside of FSM."""
    logger.info(
        f"Received unhandled message from user {message.from_user.id}: "
        f"type={message.content_type}, text={message.text[:50] if message.text else 'N/A'}"
    )

    response = (
        "💡 I'm not sure what you mean.\n\n"
        "Try one of these commands:\n"
        "/addword - Add a new word\n"
        "/bulkadd - Add many words from text\n"
        "/mywords - View your vocabulary\n"
        "/quiz - Practice your words\n"
        "/delete - Remove a word\n"
        "/help - Get help"
    )

    await message.answer(response)
