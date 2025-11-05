"""Vocabulary service for orchestrating word management and validation."""
import logging
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from agents.german_validator import german_validator, ValidationResult
from database.models import User, Word
from repositories.user_repository import UserRepository
from repositories.word_repository import WordRepository

logger = logging.getLogger(__name__)


class VocabularyService:
    """Service for managing vocabulary and validations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.word_repo = WordRepository(session)

    async def get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> User:
        """Get or create user."""
        return await self.user_repo.get_or_create(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )

    async def add_word_with_validation(
        self,
        user: User,
        german_word: str,
        translation: str
    ) -> tuple[Word, ValidationResult]:
        """
        Add a new word with article checking and translation validation.

        Args:
            user: User object
            german_word: German word (with or without article)
            translation: English translation

        Returns:
            Tuple of (Word, ValidationResult)
        """
        # Step 1: Check and add article if needed
        article_info = await german_validator.check_article(german_word)

        article = article_info.get("article")
        word_without_article = article_info.get("word")
        full_german_word = article_info.get("full_word")

        logger.info(f"Article check: {german_word} → {full_german_word} (article: {article})")

        # Step 2: Validate translation
        validation = await german_validator.validate_translation(
            full_german_word,
            translation
        )

        # Step 3: Save to database
        word = await self.word_repo.create(
            user_id=user.id,
            german_word=word_without_article,
            article=article,
            translation=translation,
            validated_by_agent=True,
            validation_feedback=validation.feedback
        )

        return word, validation

    async def add_word_without_translation(
        self,
        user: User,
        german_word: str
    ) -> tuple[Word, dict]:
        """
        Add a new word without translation (lazy loading).
        Translation will be filled in during first quiz attempt.
        Detects word type and adds article only for nouns.

        Args:
            user: User object
            german_word: German word or phrase (with or without article)

        Returns:
            Tuple of (Word, word_info dict)
        """
        # Detect word type and article (for nouns only)
        word_info = await german_validator.detect_word_type_and_article(german_word)

        article = word_info.get("article")
        word_type = word_info.get("word_type", "other")
        word_without_article = word_info.get("word")
        full_german_word = word_info.get("full_word")

        logger.info(f"Word analysis: {german_word} → {full_german_word} (type: {word_type}, article: {article})")

        # Save to database with placeholder translation
        word = await self.word_repo.create(
            user_id=user.id,
            german_word=word_without_article,
            word_type=word_type,
            article=article if word_type == "noun" else None,  # Only store article for nouns
            translation="[pending]",  # Placeholder until first quiz
            validated_by_agent=False,
            validation_feedback=None
        )

        return word, word_info

    async def get_user_words(self, user: User, limit: Optional[int] = None) -> List[Word]:
        """Get all words for a user."""
        return await self.word_repo.get_user_words(user.id, limit=limit)

    async def get_random_word_for_quiz(self, user: User) -> Optional[Word]:
        """Get a random word for quiz."""
        return await self.word_repo.get_random_word(user.id)

    async def validate_quiz_answer(
        self,
        word: Word,
        user_answer: str
    ) -> ValidationResult:
        """
        Validate quiz answer.
        If translation is pending, get correct translation from LLM and save it.

        Args:
            word: Word object
            user_answer: User's translation answer

        Returns:
            ValidationResult
        """
        # Validate using agent
        validation = await german_validator.validate_translation(
            word.full_german_word,
            user_answer
        )

        # If translation is pending, save the correct translation from LLM
        if word.translation == "[pending]":
            logger.info(f"First quiz attempt for word {word.id}, saving translation")
            # Use the correct translation from LLM, not the user's answer
            correct_translation = validation.correct_translation or user_answer
            await self.word_repo.update_translation(
                word_id=word.id,
                translation=correct_translation,
                validated_by_agent=True,
                validation_feedback=validation.feedback
            )
            # Refresh word object with new translation
            await self.session.refresh(word)

        # Update statistics
        await self.word_repo.update_review_stats(
            word.id,
            is_correct=validation.is_correct
        )

        return validation

    async def get_word_count(self, user: User) -> int:
        """Get total word count for user."""
        return await self.word_repo.count_user_words(user.id)

    async def search_words(self, user: User, search_term: str) -> List[Word]:
        """Search user's words."""
        return await self.word_repo.search_words(user.id, search_term)

    async def delete_word(self, word_id: int) -> None:
        """Delete a word."""
        await self.word_repo.delete_word(word_id)

    async def delete_word_by_text(self, user: User, german_word: str) -> bool:
        """Delete a word by German word text."""
        return await self.word_repo.delete_word_by_text(user.id, german_word)

    async def bulk_add_words(
        self,
        user: User,
        german_words: List[str]
    ) -> tuple[List[Word], List[str]]:
        """
        Bulk add multiple words without translation.
        Detects word types and filters out articles/pronouns.
        Uses batch processing for efficiency (1-2 API calls instead of N calls).

        Args:
            user: User object
            german_words: List of German words/phrases

        Returns:
            Tuple of (List of created Words, List of filtered out words)
        """
        from services.german_filters import should_filter_word

        # First pass: filter out articles and pronouns
        words_to_process = []
        filtered_words = []

        for german_word in german_words:
            if should_filter_word(german_word):
                filtered_words.append(german_word)
                logger.info(f"Filtered out: {german_word} (article/pronoun)")
            else:
                words_to_process.append(german_word)

        if not words_to_process:
            return [], filtered_words

        # Batch detect word types and articles (efficient: 1-2 API calls for all words)
        logger.info(f"Batch processing {len(words_to_process)} words for type detection")
        word_infos = await german_validator.detect_batch_word_types(words_to_process)

        # Prepare data for bulk database insert
        words_data = []
        for word_info in word_infos:
            article = word_info.get("article")
            word_type = word_info.get("word_type", "other")
            word_without_article = word_info.get("word")

            words_data.append({
                "german_word": word_without_article,
                "word_type": word_type,
                "article": article if word_type == "noun" else None,
                "translation": "[pending]",
                "validated_by_agent": False,
                "validation_feedback": None
            })

            logger.info(f"Prepared: {word_without_article} → type={word_type}, article={article}")

        # Bulk create in database
        if words_data:
            created_words = await self.word_repo.bulk_create(user.id, words_data)
        else:
            created_words = []

        return created_words, filtered_words
