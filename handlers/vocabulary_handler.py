"""Telegram handlers for vocabulary management."""
import logging

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from database.database import get_session_maker
from handlers.states import AddWordStates, QuizStates, ImageOCRStates, BulkAddStates
from services.vocabulary_service import VocabularyService
from services.ocr_service import extract_german_words
from services.text_parser import text_parser

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
        "💡 Tips:\n"
        "• If you don't include the article (der/die/das), I'll add it for you!\n"
        "• You'll learn the translation during your first quiz!"
    )


@router.message(AddWordStates.waiting_for_german)
async def process_german_word(message: types.Message, state: FSMContext) -> None:
    """Process the German word input and save without translation."""
    german_word = message.text.strip()

    if not german_word:
        await message.answer("Please enter a valid German word.")
        return

    # Show processing message
    processing_msg = await message.answer("🤔 Checking the article...")

    try:
        # Get session and service
        session_maker = get_session_maker()
        async with session_maker() as session:
            vocab_service = get_vocabulary_service(session)

            # Get or create user
            user = await vocab_service.get_or_create_user(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )

            # Add word without translation
            word, article_info = await vocab_service.add_word_without_translation(
                user=user,
                german_word=german_word
            )

            # Delete processing message
            await processing_msg.delete()

            # Prepare response
            response = f"✨ <b>Word added!</b>\n\n"
            response += f"📖 <b>{word.full_german_word}</b>\n\n"

            if article_info.get("article"):
                response += f"💡 Article: {article_info.get('article')}\n"

            response += f"\n🎯 Use /quiz to learn the translation!\n"

            # Show word count
            word_count = await vocab_service.get_word_count(user)
            response += f"📊 Total words: {word_count}"

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
# /delete command - Delete a word from vocabulary
# ============================================================================

@router.message(Command("delete"))
async def cmd_delete(message: types.Message) -> None:
    """Delete a word from vocabulary."""
    logger.info(f"User {message.from_user.id} requested /delete")

    # Extract the word from the command
    # Format: /delete hund  or  /delete der Hund
    command_parts = message.text.split(maxsplit=1)

    if len(command_parts) < 2:
        await message.answer(
            "❌ Please specify a word to delete.\n\n"
            "Usage: /delete <word>\n"
            "Examples:\n"
            "• /delete hund\n"
            "• /delete der Hund\n"
            "• /delete Tisch"
        )
        return

    german_word = command_parts[1].strip()

    try:
        session_maker = get_session_maker()
        async with session_maker() as session:
            vocab_service = get_vocabulary_service(session)

            # Get or create user
            user = await vocab_service.get_or_create_user(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )

            # Delete the word
            deleted = await vocab_service.delete_word_by_text(user, german_word)

            if deleted:
                # Show success message
                word_count = await vocab_service.get_word_count(user)
                await message.answer(
                    f"✅ <b>Deleted!</b>\n\n"
                    f"Removed '<b>{german_word}</b>' from your vocabulary.\n\n"
                    f"📊 Words remaining: {word_count}",
                    parse_mode="HTML"
                )
                logger.info(f"User {message.from_user.id} deleted word: {german_word}")
            else:
                await message.answer(
                    f"❌ <b>Word not found</b>\n\n"
                    f"Could not find '<b>{german_word}</b>' in your vocabulary.\n\n"
                    f"💡 Tip: Use /mywords to see your vocabulary list.",
                    parse_mode="HTML"
                )

    except Exception as e:
        logger.error(f"Error deleting word: {e}")
        await message.answer("❌ Sorry, couldn't delete the word. Please try again.")


# ============================================================================
# /mywords command - List user's vocabulary
# ============================================================================

@router.message(Command("mywords"))
async def cmd_mywords(message: types.Message) -> None:
    """Show user's vocabulary list."""
    logger.info(f"User {message.from_user.id} requested /mywords")

    try:
        session_maker = get_session_maker()
        async with session_maker() as session:
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

                # Show pending translations differently
                translation_display = word.translation if word.translation != "[pending]" else "❓ <i>Practice to learn!</i>"

                response += f"{i}. <b>{word.full_german_word}</b> = {translation_display}{stats}\n"

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
        session_maker = get_session_maker()
        async with session_maker() as session:
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

        session_maker = get_session_maker()
        async with session_maker() as session:
            vocab_service = get_vocabulary_service(session)

            # Get word
            word = await vocab_service.word_repo.get_by_id(word_id)
            if not word:
                await processing_msg.delete()
                await message.answer("❌ Error: Word not found.")
                await state.clear()
                return

            # Check if this is first quiz (translation pending)
            is_first_quiz = word.translation == "[pending]"

            # Validate answer (this will also save translation if pending)
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

            # Special message for first quiz
            if is_first_quiz:
                response += f"🎉 <b>First attempt at this word!</b>\n\n"

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


# ============================================================================
# /addphoto command & Image OCR - Add words from photos
# ============================================================================

@router.message(Command("addphoto"))
async def cmd_addphoto(message: types.Message, state: FSMContext) -> None:
    """Start the add words from photo flow."""
    logger.info(f"User {message.from_user.id} started /addphoto")

    await state.set_state(ImageOCRStates.waiting_for_image)
    await message.answer(
        "📸 <b>Add Words from Photo</b>\n\n"
        "Send me a photo or document containing German words!\n\n"
        "💡 <b>Tips for best results:</b>\n"
        "• Clear, well-lit images work best\n"
        "• Avoid blurry or low-resolution photos\n"
        "• Printed text works better than handwriting\n\n"
        "I'll extract the German words and let you review them before saving.",
        parse_mode="HTML"
    )


@router.message(ImageOCRStates.waiting_for_image, F.photo | F.document)
async def process_image_upload(message: types.Message, state: FSMContext) -> None:
    """Process uploaded image and extract German words."""
    logger.info(f"User {message.from_user.id} uploaded image for OCR")

    # Show processing message
    processing_msg = await message.answer("🔍 Processing image and extracting words...")

    try:
        # Get the file
        if message.photo:
            # Get largest photo size
            photo = message.photo[-1]
            file = await message.bot.get_file(photo.file_id)
        elif message.document:
            file = await message.bot.get_file(message.document.file_id)
        else:
            await processing_msg.delete()
            await message.answer("❌ Please send a photo or document.")
            return

        # Download file
        image_data = await message.bot.download_file(file.file_path)
        image_bytes = image_data.read()

        # Extract German words using OCR
        words, confidences = await extract_german_words(image_bytes)

        # Delete processing message
        await processing_msg.delete()

        if not words:
            await message.answer(
                "❌ <b>No words found</b>\n\n"
                "I couldn't extract any German words from this image.\n\n"
                "💡 Try:\n"
                "• A clearer or higher-resolution image\n"
                "• Better lighting\n"
                "• Making sure the text is visible and in focus",
                parse_mode="HTML"
            )
            await state.clear()
            return

        # Save words to state for review
        await state.update_data(
            extracted_words=words,
            confidences=confidences
        )
        await state.set_state(ImageOCRStates.reviewing_words)

        # Show extracted words for review
        response = f"✨ <b>Found {len(words)} words!</b>\n\n"
        response += "📝 <b>Extracted words:</b>\n"

        for i, word in enumerate(words, 1):
            response += f"{i}. {word}\n"

        response += "\n💡 <b>What would you like to do?</b>\n"
        response += "• Type <b>'OK'</b> or <b>'Save'</b> to add all words\n"
        response += "• Type <b>'Remove 3,5,7'</b> to skip certain words\n"
        response += "• Type <b>'Cancel'</b> to discard everything"

        await message.answer(response, parse_mode="HTML")

        logger.info(f"User {message.from_user.id} reviewing {len(words)} extracted words")

    except Exception as e:
        logger.error(f"Error processing image: {e}")
        await processing_msg.delete()
        await message.answer(
            "❌ Sorry, something went wrong while processing the image.\n\n"
            "Please try again with a different photo."
        )
        await state.clear()


@router.message(ImageOCRStates.reviewing_words)
async def process_word_review(message: types.Message, state: FSMContext) -> None:
    """Process user's review/correction of extracted words."""
    user_input = message.text.strip().lower()

    if not user_input:
        await message.answer("Please provide a response.")
        return

    try:
        # Get saved data
        data = await state.get_data()
        words = data.get("extracted_words", [])

        if not words:
            await message.answer("❌ No words to process.")
            await state.clear()
            return

        # Handle different commands
        if user_input in ["cancel", "abort", "stop"]:
            await message.answer("❌ Cancelled. No words were added.")
            await state.clear()
            return

        elif user_input in ["ok", "save", "yes", "confirm"]:
            # Save all words
            final_words = words

        elif user_input.startswith("remove "):
            # Parse indices to remove
            try:
                indices_str = user_input.replace("remove ", "").strip()
                indices = [int(i.strip()) - 1 for i in indices_str.split(",")]

                # Validate indices
                indices = [i for i in indices if 0 <= i < len(words)]

                # Remove selected words
                final_words = [w for i, w in enumerate(words) if i not in indices]

                if not final_words:
                    await message.answer("❌ All words removed. Nothing to save.")
                    await state.clear()
                    return

            except ValueError:
                await message.answer(
                    "❌ Invalid format. Use: <b>Remove 1,3,5</b>",
                    parse_mode="HTML"
                )
                return

        else:
            await message.answer(
                "❌ Invalid command.\n\n"
                "Use:\n"
                "• <b>'OK'</b> to save all words\n"
                "• <b>'Remove 1,3,5'</b> to skip specific words\n"
                "• <b>'Cancel'</b> to discard",
                parse_mode="HTML"
            )
            return

        # Save words to database
        processing_msg = await message.answer("💾 Saving words...")

        session_maker = get_session_maker()
        async with session_maker() as session:
            vocab_service = get_vocabulary_service(session)

            # Get or create user
            user = await vocab_service.get_or_create_user(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )

            # Add each word
            saved_count = 0
            for word in final_words:
                try:
                    await vocab_service.add_word_without_translation(user, word)
                    saved_count += 1
                except Exception as e:
                    logger.warning(f"Error saving word '{word}': {e}")

            # Get total word count
            total_words = await vocab_service.get_word_count(user)

            # Delete processing message
            await processing_msg.delete()

            # Show success message
            await message.answer(
                f"✅ <b>Success!</b>\n\n"
                f"Added <b>{saved_count}</b> words to your vocabulary!\n\n"
                f"📊 Total words: {total_words}\n\n"
                f"💡 Use /quiz to practice them!",
                parse_mode="HTML"
            )

            # Clear state
            await state.clear()

            logger.info(f"User {message.from_user.id} saved {saved_count} words from OCR")

    except Exception as e:
        logger.error(f"Error saving OCR words: {e}")
        await message.answer("❌ Sorry, couldn't save the words. Please try again.")
        await state.clear()


# ============================================================================
# /bulkadd command - Add multiple words from pasted text
# ============================================================================

@router.message(Command("bulkadd"))
async def cmd_bulkadd(message: types.Message, state: FSMContext) -> None:
    """Start the bulk add words flow."""
    logger.info(f"User {message.from_user.id} started /bulkadd")

    await state.set_state(BulkAddStates.waiting_for_text)
    await message.answer(
        "📋 <b>Bulk Add Vocabulary</b>\n\n"
        "Paste your German vocabulary list here!\n\n"
        "I'll extract German words from any format:\n"
        "• Mixed with Russian/English translations\n"
        "• With verb conjugations\n"
        "• With grammar notes\n\n"
        "<b>Example:</b>\n"
        "<code>der Eigentümer,-= der Besitzer,/ владелец\n"
        "anfangen fing an angefangen начинаться\n"
        "Anfang Oktober\n"
        "sich entwickeln развиваться</code>\n\n"
        "Just paste your list and I'll extract the German words!",
        parse_mode="HTML"
    )


@router.message(BulkAddStates.waiting_for_text)
async def process_bulk_text(message: types.Message, state: FSMContext) -> None:
    """Process pasted bulk text and extract German words."""
    bulk_text = message.text.strip()

    if not bulk_text:
        await message.answer("Please paste your vocabulary list.")
        return

    # Show processing message
    processing_msg = await message.answer("🔍 Parsing text and extracting German words...")

    try:
        # Parse text and extract German words
        extracted_words = text_parser.parse_bulk_text(bulk_text)

        # Delete processing message
        await processing_msg.delete()

        if not extracted_words:
            await message.answer(
                "❌ <b>No German words found</b>\n\n"
                "I couldn't extract any German words from your text.\n\n"
                "💡 Make sure your text contains German vocabulary.\n"
                "Try adding at least one clear German word or phrase.",
                parse_mode="HTML"
            )
            await state.clear()
            return

        # Save words to state for review
        await state.update_data(extracted_words=extracted_words)
        await state.set_state(BulkAddStates.reviewing_words)

        # Show extracted words for review (limit display to first 30)
        response = f"✨ <b>Found {len(extracted_words)} words!</b>\n\n"
        response += "📝 <b>Extracted German words:</b>\n"

        display_count = min(len(extracted_words), 30)
        for i in range(display_count):
            word = extracted_words[i]
            response += f"{i+1}. {word}\n"

        if len(extracted_words) > 30:
            response += f"\n<i>... and {len(extracted_words) - 30} more</i>\n"

        response += "\n💡 <b>What would you like to do?</b>\n"
        response += "• Type <b>'OK'</b> or <b>'Save'</b> to add all words\n"
        response += "• Type <b>'Remove 3,5,7'</b> to skip specific words\n"
        response += "• Type <b>'Cancel'</b> to discard everything"

        await message.answer(response, parse_mode="HTML")

        logger.info(f"User {message.from_user.id} reviewing {len(extracted_words)} extracted words from bulk text")

    except Exception as e:
        logger.error(f"Error parsing bulk text: {e}")
        await processing_msg.delete()
        await message.answer(
            "❌ Sorry, something went wrong while parsing your text.\n\n"
            "Please try again with a different format."
        )
        await state.clear()


@router.message(BulkAddStates.reviewing_words)
async def process_bulk_review(message: types.Message, state: FSMContext) -> None:
    """Process user's review of extracted words from bulk text."""
    user_input = message.text.strip().lower()

    if not user_input:
        await message.answer("Please provide a response.")
        return

    try:
        # Get saved data
        data = await state.get_data()
        words = data.get("extracted_words", [])

        if not words:
            await message.answer("❌ No words to process.")
            await state.clear()
            return

        # Handle different commands
        if user_input in ["cancel", "abort", "stop"]:
            await message.answer("❌ Cancelled. No words were added.")
            await state.clear()
            return

        elif user_input in ["ok", "save", "yes", "confirm"]:
            # Save all words
            final_words = words

        elif user_input.startswith("remove "):
            # Parse indices to remove
            try:
                indices_str = user_input.replace("remove ", "").strip()
                indices = [int(i.strip()) - 1 for i in indices_str.split(",")]

                # Validate indices
                indices = [i for i in indices if 0 <= i < len(words)]

                # Remove selected words
                final_words = [w for i, w in enumerate(words) if i not in indices]

                if not final_words:
                    await message.answer("❌ All words removed. Nothing to save.")
                    await state.clear()
                    return

            except ValueError:
                await message.answer(
                    "❌ Invalid format. Use: <b>Remove 1,3,5</b>",
                    parse_mode="HTML"
                )
                return

        else:
            await message.answer(
                "❌ Invalid command.\n\n"
                "Use:\n"
                "• <b>'OK'</b> to save all words\n"
                "• <b>'Remove 1,3,5'</b> to skip specific words\n"
                "• <b>'Cancel'</b> to discard",
                parse_mode="HTML"
            )
            return

        # Save words to database using bulk operation
        processing_msg = await message.answer("💾 Analyzing and saving words...")

        session_maker = get_session_maker()
        async with session_maker() as session:
            vocab_service = get_vocabulary_service(session)

            # Get or create user
            user = await vocab_service.get_or_create_user(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )

            # Bulk add words (automatically detects types, articles, and filters pronouns/articles)
            created_words, filtered_words = await vocab_service.bulk_add_words(user, final_words)

            saved_count = len(created_words)
            filtered_count = len(filtered_words)

            # Get total word count
            total_words = await vocab_service.get_word_count(user)

            # Delete processing message
            await processing_msg.delete()

            # Show success message
            success_msg = (
                f"✅ <b>Success!</b>\n\n"
                f"Added <b>{saved_count}</b> words to your vocabulary!\n\n"
            )

            if filtered_count > 0:
                success_msg += f"🔍 Filtered out {filtered_count} articles/pronouns\n\n"

            success_msg += (
                f"📊 Total words: {total_words}\n\n"
                f"💡 Use /quiz to practice them!"
            )

            await message.answer(success_msg, parse_mode="HTML")

            # Clear state
            await state.clear()

            logger.info(f"User {message.from_user.id} saved {saved_count} words from bulk text (filtered {filtered_count})")

    except Exception as e:
        logger.error(f"Error saving bulk words: {e}")
        await message.answer("❌ Sorry, couldn't save the words. Please try again.")
        await state.clear()
