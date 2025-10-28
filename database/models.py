"""Database models for vocabulary learning."""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, String, Integer, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base


class User(Base):
    """User model for storing Telegram user information."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    language_preference: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_active: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    words: Mapped[list["Word"]] = relationship("Word", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"


class Word(Base):
    """Word model for storing German vocabulary and translations."""

    __tablename__ = "words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    german_word: Mapped[str] = mapped_column(String(255), nullable=False)
    article: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # der, die, das
    translation: Mapped[str] = mapped_column(String(255), nullable=False)

    # Validation and feedback
    validated_by_agent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validation_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Learning progress
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    incorrect_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    date_added: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_reviewed: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)  # active, archived, deleted

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="words")

    def __repr__(self) -> str:
        article_part = f"{self.article} " if self.article else ""
        return f"<Word({article_part}{self.german_word} = {self.translation})>"

    @property
    def full_german_word(self) -> str:
        """Return German word with article if available."""
        if self.article:
            return f"{self.article} {self.german_word}"
        return self.german_word

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_reviews == 0:
            return 0.0
        return (self.correct_count / self.total_reviews) * 100
