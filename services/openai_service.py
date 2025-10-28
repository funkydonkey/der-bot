"""OpenAI API service."""
import logging
from typing import Optional

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from config.settings import settings

logger = logging.getLogger(__name__)

# Global client instance
client: Optional[AsyncOpenAI] = None


def init_openai() -> None:
    """Initialize OpenAI client."""
    global client

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        logger.info("✓ OpenAI client initialized")
    except Exception as e:
        logger.error(f"✗ OpenAI client initialization failed: {e}")
        raise


async def test_openai_connection() -> None:
    """Test OpenAI API connection with a simple request."""
    if client is None:
        raise RuntimeError("OpenAI client not initialized")

    try:
        response: ChatCompletion = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "ping"}
            ],
            max_tokens=10
        )
        logger.info(f"✓ OpenAI API connection successful (response: {response.choices[0].message.content})")
    except Exception as e:
        logger.error(f"✗ OpenAI API connection failed: {e}")
        raise


async def generate_completion(
    prompt: str,
    model: str = "gpt-3.5-turbo",
    max_tokens: int = 500
) -> str:
    """Generate a completion using OpenAI API."""
    if client is None:
        raise RuntimeError("OpenAI client not initialized")

    try:
        response: ChatCompletion = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"OpenAI completion error: {e}")
        raise
