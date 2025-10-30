"""MCP OCR service for extracting German text from images."""
import logging
import re
from io import BytesIO
from typing import Optional, List, Tuple

import httpx
from PIL import Image

from config.settings import settings

logger = logging.getLogger(__name__)

# Global HTTP client
client: Optional[httpx.AsyncClient] = None


def init_ocr_client() -> None:
    """Initialize OCR HTTP client."""
    global client

    try:
        client = httpx.AsyncClient(
            base_url=settings.mcp_ocr_endpoint,
            timeout=30.0
        )
        logger.info("✓ MCP OCR client initialized")
    except Exception as e:
        logger.error(f"✗ MCP OCR client initialization failed: {e}")
        raise


async def test_ocr_connection() -> None:
    """Test MCP OCR server connection with a health check."""
    if client is None:
        raise RuntimeError("MCP OCR client not initialized")

    try:
        # Try common health check endpoints
        health_endpoints = ["/health", "/healthz", "/status", "/ping"]

        for endpoint in health_endpoints:
            try:
                response = await client.get(endpoint)
                if response.status_code == 200:
                    logger.info(f"✓ MCP OCR server connection successful (endpoint: {endpoint})")
                    return
            except httpx.HTTPError:
                continue

        # If no health endpoint works, just verify the base URL is reachable
        response = await client.get("/")
        logger.info(f"✓ MCP OCR server is reachable (status: {response.status_code})")

    except Exception as e:
        logger.warning(f"⚠ MCP OCR server health check failed (non-blocking): {e}")
        # Don't raise - OCR is optional for basic bot functionality


async def extract_german_words(image_data: bytes) -> Tuple[List[str], List[float]]:
    """
    Extract German words from image using MCP OCR.

    Args:
        image_data: Image file as bytes

    Returns:
        Tuple of (words_list, confidence_scores)
    """
    if client is None:
        raise RuntimeError("MCP OCR client not initialized")

    try:
        # Preprocess image for better OCR accuracy
        preprocessed_data = _preprocess_image(image_data)

        # Call MCP OCR server with German language
        response = await client.post(
            "/ocr",
            files={"image": preprocessed_data},
            data={"lang": "deu"}  # German language model
        )
        response.raise_for_status()

        result = response.json()
        raw_text = result.get("text", "")

        # Extract and clean words
        words = _extract_words_from_text(raw_text)

        # Get confidence scores (if available from MCP)
        confidences = result.get("confidences", [90.0] * len(words))

        logger.info(f"Extracted {len(words)} German words from image")
        return words, confidences

    except Exception as e:
        logger.error(f"OCR word extraction error: {e}")
        return [], []


async def process_image_ocr(image_data: bytes) -> str:
    """Process image with OCR and return extracted text (legacy function)."""
    if client is None:
        raise RuntimeError("MCP OCR client not initialized")

    try:
        response = await client.post(
            "/ocr",
            files={"image": image_data},
            data={"lang": "deu"}  # German language
        )
        response.raise_for_status()

        result = response.json()
        return result.get("text", "")

    except Exception as e:
        logger.error(f"OCR processing error: {e}")
        raise


def _preprocess_image(image_data: bytes) -> bytes:
    """
    Preprocess image for better OCR accuracy.

    Args:
        image_data: Original image bytes

    Returns:
        Preprocessed image bytes
    """
    try:
        # Open image from bytes
        image = Image.open(BytesIO(image_data))

        # Convert to grayscale
        image = image.convert('L')

        # Resize if too small (improve OCR accuracy)
        width, height = image.size
        if width < 1000 or height < 1000:
            scale_factor = max(1000 / width, 1000 / height)
            new_size = (int(width * scale_factor), int(height * scale_factor))
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        # Increase contrast (simple threshold for binarization)
        threshold = 128
        image = image.point(lambda p: 255 if p > threshold else 0)

        # Convert back to bytes
        output = BytesIO()
        image.save(output, format='PNG')
        return output.getvalue()

    except Exception as e:
        logger.warning(f"Image preprocessing failed, using original: {e}")
        return image_data


def _extract_words_from_text(text: str) -> List[str]:
    """
    Extract valid German words from OCR text.

    Args:
        text: Raw OCR text output

    Returns:
        List of cleaned German words
    """
    # Split text into words
    raw_words = text.split()

    words = []
    seen = set()

    for word in raw_words:
        # Clean word
        cleaned = _clean_word(word)

        # Validate and add if unique
        if cleaned and _is_valid_german_word(cleaned):
            word_lower = cleaned.lower()
            if word_lower not in seen:
                seen.add(word_lower)
                words.append(cleaned)

    return words


def _clean_word(word: str) -> str:
    """
    Clean OCR output word.

    Args:
        word: Raw OCR word

    Returns:
        Cleaned word
    """
    # Remove leading/trailing punctuation
    word = word.strip('.,;:!?"\'()[]{}«»""''')

    # Remove any non-letter characters except umlauts and ß
    word = re.sub(r'[^a-zA-ZäöüÄÖÜß]', '', word)

    return word.strip()


def _is_valid_german_word(word: str) -> bool:
    """
    Basic validation for German words.

    Args:
        word: Word to validate

    Returns:
        True if likely a valid German word
    """
    # Minimum length check
    if len(word) < 2:
        return False

    # Must contain at least one letter
    if not re.search(r'[a-zA-ZäöüÄÖÜß]', word):
        return False

    # Must start with a letter
    if not word[0].isalpha():
        return False

    return True


async def close_ocr_client() -> None:
    """Close OCR HTTP client."""
    global client

    if client:
        await client.aclose()
        logger.info("MCP OCR client closed")
