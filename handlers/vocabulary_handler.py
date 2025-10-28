"""Telegram handlers for vocabulary management."""
import logging

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database.database import async_session_maker
from handlers.states import AddWordStates, QuizStates
from services.vocabulary_service import VocabularyService

logger = logging.getLogger(__name__)

# Create router
router = Router()


def get_vocabulary_service(session):
    """Get vocabulary service instance."""
    return VocabularyService(session)


# ============================================================================
# /addword command - Add new vocabulary
# ============================================================================

@router.message(Command("addword"))
async def cmd_addword(message: types.Message, state: FSMContext) -> None:
    """Start the add word flow."""
    logger.info(f"User {message.from_user.id} started /addword")

    await state.set_state(AddWordStates.waiting_for_german)
    await message.answer(
        "📝 Let's add a new German word!\n\n"
        "Enter the German word (with or without article):\n"
        "Examples: 'Hund' or 'der Hund'\n\n"
        "💡 Tip: If you don't include the article (der/die/das), "
        "I'll add it for you!"
    )


@router.message(AddWordStates.waiting_for_german)
async def process_german_word(message: types.Message, state: FSMContext) -> None:
    """Process the German word input."""
    german_word = message.text.strip()

    if not german_word:
        await message.answer("Please enter a valid German word.")
        return

    # Save German word to state
    await state.update_data(german_word=german_word)
    await state.set_state(AddWordStates.waiting_for_translation)

    await message.answer(
        f"✅ Got it: <b>{german_word}</b>\n\n"
        f"Now enter the English translation:",
        parse_mode="HTML"
    )


@router.message(AddWordStates.waiting_for_translation)
async def process_translation(message: types.Message, state: FSMContext) -> None:
    """Process the translation and validate with agent."""
    translation = message.text.strip()

    if not translation:
        await message.answer("Please enter a valid translation.")
        return

    # Get saved data
    data = await state.get_data()
    german_word = data.get("german_word")

    # Show processing message
    processing_msg = await message.answer("🤔 Checking your translation...")

    try:
        # Get session and service
        async with async_session_maker() as session:
            vocab_service = get_vocabulary_service(session)

            # Get or create user
            user = await vocab_service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )

        # Add word with validation
        word, validation = await vocab_service.add_word_with_validation(
            user=user,
            german_word=german_word,
            translation=translation
        )

        # Delete processing message
        await processing_msg.delete()

        # Prepare response
        if validation.is_correct:
            response = f"✅ <b>Correct!</b>\n\n"
        else:
            response = f"⚠️ <b>Not quite right</b>\n\n"

        response += f"📖 <b>{word.full_german_word}</b> = {translation}\n\n"
        response += f"💬 {validation.feedback}\n\n"
        response += f"✨ Word saved to your vocabulary!"

        # Show word count
        word_count = await vocab_service.get_word_count(user)
        response += f"\n📊 Total words: {word_count}"

        await message.answer(response, parse_mode="HTML")

        # Clear state
        await state.clear()

        logger.info(f"User {message.from_user.id} added word: {word.full_german_word}")

    except Exception as e:
        logger.error(f"Error adding word: {e}")
        await processing_msg.delete()
        await message.answer(
            "❌ Sorry, something went wrong. Please try again later."
        )
        await state.clear()


# ============================================================================
# /mywords command - List user's vocabulary
# ============================================================================

@router.message(Command("mywords"))
async def cmd_mywords(message: types.Message) -> None:
    """Show user's vocabulary list."""
    logger.info(f"User {message.from_user.id} requested /mywords")

    try:
        async with async_session_maker() as session:
            vocab_service = get_vocabulary_service(session)

            # Get or create user
            user = await vocab_service.get_or_create_user(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )

            # Get words
            words = await vocab_service.get_user_words(user, limit=50)

            if not words:
                await message.answer(
                    "📚 Your vocabulary is empty!\n\n"
                    "Use /addword to add your first German word."
                )
                return

            # Format word list
            response = f"📚 <b>Your Vocabulary ({len(words)} words)</b>\n\n"

            for i, word in enumerate(words, 1):
                success_rate = word.success_rate
                stats = f" [{word.correct_count}✓/{word.incorrect_count}✗]" if word.total_reviews > 0 else ""

                response += f"{i}. <b>{word.full_german_word}</b> = {word.translation}{stats}\n"

                # Split into multiple messages if too long
                if len(response) > 3500:
                    await message.answer(response, parse_mode="HTML")
                    response = ""

            if response:
                await message.answer(response, parse_mode="HTML")

            # Show quiz suggestion
            await message.answer(
                "\n💡 Ready to practice? Use /quiz to test yourself!",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Error listing words: {e}")
        await message.answer("❌ Sorry, couldn't load your vocabulary.")


# ============================================================================
# /quiz command - Practice vocabulary
# ============================================================================

@router.message(Command("quiz"))
async def cmd_quiz(message: types.Message, state: FSMContext) -> None:
    """Start a vocabulary quiz."""
    logger.info(f"User {message.from_user.id} started /quiz")

    try:
        async with async_session_maker() as session:
            vocab_service = get_vocabulary_service(session)

            # Get or create user
            user = await vocab_service.get_or_create_user(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )

            # Get random word
            word = await vocab_service.get_random_word_for_quiz(user)

            if not word:
                await message.answer(
                    "📚 You don't have any words yet!\n\n"
                    "Use /addword to add some vocabulary first."
                )
                return

            # Save word ID to state
            await state.update_data(word_id=word.id)
            await state.set_state(QuizStates.waiting_for_answer)

            # Ask for translation
            await message.answer(
                f"🎯 <b>Quiz Time!</b>\n\n"
                f"Translate this German word to English:\n\n"
                f"<b>{word.full_german_word}</b>\n\n"
                f"Your answer:",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Error starting quiz: {e}")
        await message.answer("❌ Sorry, couldn't start the quiz.")


@router.message(QuizStates.waiting_for_answer)
async def process_quiz_answer(message: types.Message, state: FSMContext) -> None:
    """Process the quiz answer."""
    user_answer = message.text.strip()

    if not user_answer:
        await message.answer("Please provide an answer.")
        return

    # Show processing
    processing_msg = await message.answer("🤔 Checking your answer...")

    try:
        # Get saved data
        data = await state.get_data()
        word_id = data.get("word_id")

        async with async_session_maker() as session:
            vocab_service = get_vocabulary_service(session)

            # Get word
            word = await vocab_service.word_repo.get_by_id(word_id)
            if not word:
                await processing_msg.delete()
                await message.answer("❌ Error: Word not found.")
                await state.clear()
                return

            # Validate answer
            validation = await vocab_service.validate_quiz_answer(word, user_answer)

            # Delete processing message
            await processing_msg.delete()

            # Prepare response
            if validation.is_correct:
                emoji = "✅"
                title = "<b>Correct!</b>"
            else:
                emoji = "❌"
                title = "<b>Not quite!</b>"

            response = f"{emoji} {title}\n\n"
            response += f"📖 <b>{word.full_german_word}</b> = {word.translation}\n\n"
            response += f"💬 {validation.feedback}\n\n"

            # Show stats
            response += f"📊 Your stats for this word:\n"
            response += f"   Correct: {word.correct_count} | Incorrect: {word.incorrect_count}\n"
            response += f"   Success rate: {word.success_rate:.0f}%"

            await message.answer(response, parse_mode="HTML")

            # Clear state
            await state.clear()

            # Offer another quiz
            await message.answer(
                "Want to practice more? Use /quiz again!",
                parse_mode="HTML"
            )

            logger.info(f"User {message.from_user.id} answered quiz: {validation.is_correct}")

    except Exception as e:
        logger.error(f"Error processing quiz answer: {e}")
        await processing_msg.delete()
        await message.answer("❌ Sorry, couldn't check your answer.")
        await state.clear()
