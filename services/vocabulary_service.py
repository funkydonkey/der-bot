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
