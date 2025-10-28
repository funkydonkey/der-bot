"""User repository for database operations."""
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for User model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_preference: str = "en"
    ) -> User:
        """Create a new user."""
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_preference=language_preference
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        logger.info(f"Created new user: {telegram_id} ({username})")
        return user

    async def get_or_create(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> User:
        """Get existing user or create new one."""
        user = await self.get_by_telegram_id(telegram_id)

        if user is None:
            user = await self.create(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
        else:
            # Update user info if changed
            if username and user.username != username:
                user.username = username
            if first_name and user.first_name != first_name:
                user.first_name = first_name
            if last_name and user.last_name != last_name:
                user.last_name = last_name

            await self.session.commit()
            await self.session.refresh(user)

        return user

    async def update_last_active(self, user_id: int) -> None:
        """Update user's last active timestamp."""
        user = await self.session.get(User, user_id)
        if user:
            from datetime import datetime
            user.last_active = datetime.utcnow()
            await self.session.commit()
