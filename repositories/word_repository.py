"""Word repository for database operations."""
import logging
from datetime import datetime
from typing import Optional, List
from random import choice

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Word

logger = logging.getLogger(__name__)


class WordRepository:
    """Repository for Word model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: int,
        german_word: str,
        translation: str,
        article: Optional[str] = None,
        validated_by_agent: bool = False,
        validation_feedback: Optional[str] = None
    ) -> Word:
        """Create a new word."""
        word = Word(
            user_id=user_id,
            german_word=german_word,
            article=article,
            translation=translation,
            validated_by_agent=validated_by_agent,
            validation_feedback=validation_feedback
        )
        self.session.add(word)
        await self.session.commit()
        await self.session.refresh(word)

        logger.info(f"Created word: {word.full_german_word} = {translation} for user {user_id}")
        return word

    async def get_by_id(self, word_id: int) -> Optional[Word]:
        """Get word by ID."""
        return await self.session.get(Word, word_id)

    async def get_user_words(
        self,
        user_id: int,
        status: str = "active",
        limit: Optional[int] = None
    ) -> List[Word]:
        """Get all words for a user."""
        query = select(Word).where(
            Word.user_id == user_id,
            Word.status == status
        ).order_by(Word.date_added.desc())

        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_random_word(self, user_id: int, status: str = "active") -> Optional[Word]:
        """Get a random word for quiz."""
        words = await self.get_user_words(user_id, status)
        return choice(words) if words else None

    async def count_user_words(self, user_id: int, status: str = "active") -> int:
        """Count total words for a user."""
        result = await self.session.execute(
            select(func.count(Word.id)).where(
                Word.user_id == user_id,
                Word.status == status
            )
        )
        return result.scalar() or 0

    async def update_translation(
        self,
        word_id: int,
        translation: str,
        validated_by_agent: bool = True,
        validation_feedback: Optional[str] = None
    ) -> Word:
        """Update word translation (for lazy loading)."""
        word = await self.get_by_id(word_id)
        if not word:
            raise ValueError(f"Word {word_id} not found")

        word.translation = translation
        word.validated_by_agent = validated_by_agent
        word.validation_feedback = validation_feedback

        await self.session.commit()
        await self.session.refresh(word)

        logger.info(f"Updated translation for word {word_id}: {translation}")
        return word

    async def update_review_stats(
        self,
        word_id: int,
        is_correct: bool
    ) -> Word:
        """Update word review statistics."""
        word = await self.get_by_id(word_id)
        if not word:
            raise ValueError(f"Word {word_id} not found")

        word.total_reviews += 1
        word.last_reviewed = datetime.utcnow()

        if is_correct:
            word.correct_count += 1
        else:
            word.incorrect_count += 1

        await self.session.commit()
        await self.session.refresh(word)

        logger.info(f"Updated stats for word {word_id}: correct={is_correct}")
        return word

    async def delete_word(self, word_id: int) -> None:
        """Soft delete a word by setting status to 'deleted'."""
        word = await self.get_by_id(word_id)
        if word:
            word.status = "deleted"
            await self.session.commit()
            logger.info(f"Deleted word {word_id}")

    async def search_words(
        self,
        user_id: int,
        search_term: str,
        status: str = "active"
    ) -> List[Word]:
        """Search words by German word or translation."""
        query = select(Word).where(
            Word.user_id == user_id,
            Word.status == status
        ).where(
            (Word.german_word.ilike(f"%{search_term}%")) |
            (Word.translation.ilike(f"%{search_term}%"))
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())
