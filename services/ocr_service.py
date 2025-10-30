"""OCR.space service for extracting German text from images."""
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
    """Initialize OCR HTTP client for OCR.space."""
    global client

    if not settings.ocr_api_key:
        logger.warning("⚠ OCR_API_KEY not set - /addphoto command will not work")
        logger.info("Get a free API key at: https://ocr.space/ocrapi")
        return

    try:
        client = httpx.AsyncClient(
            timeout=30.0
        )
        logger.info("✓ OCR.space client initialized")
    except Exception as e:
        logger.error(f"✗ OCR client initialization failed: {e}")
        raise


async def test_ocr_connection() -> None:
    """Test OCR.space API connection."""
    if not settings.ocr_api_key:
        logger.warning("⚠ OCR API key not configured - skipping connection test")
        return

    if client is None:
        logger.warning("⚠ OCR client not initialized")
        return

    try:
        # Simple test with minimal payload
        response = await client.post(
            settings.ocr_api_endpoint,
            headers={"apikey": settings.ocr_api_key},
            data={"url": "https://api.ocr.space/Content/Images/receipt-ocr-original.jpg"}
        )

        if response.status_code == 200:
            result = response.json()
            if not result.get("IsErroredOnProcessing", True):
                logger.info("✓ OCR.space API connection successful")
                return
            else:
                logger.warning(f"⚠ OCR.space API error: {result.get('ErrorMessage')}")
        else:
            logger.warning(f"⚠ OCR.space API returned status {response.status_code}")

    except Exception as e:
        logger.warning(f"⚠ OCR.space API health check failed (non-blocking): {e}")
        # Don't raise - OCR is optional for basic bot functionality


async def extract_german_words(image_data: bytes) -> Tuple[List[str], List[float]]:
    """
    Extract German words from image using OCR.space.

    Args:
        image_data: Image file as bytes

    Returns:
        Tuple of (words_list, confidence_scores)
    """
    if client is None:
        raise RuntimeError("OCR client not initialized")

    if not settings.ocr_api_key:
        raise RuntimeError("OCR API key not configured")

    try:
        # Preprocess image for better OCR accuracy
        preprocessed_data = _preprocess_image(image_data)

        # Prepare multipart form data for OCR.space API
        files = {
            "file": ("image.png", preprocessed_data, "image/png")
        }

        data = {
            "language": "ger",  # German language
            "isOverlayRequired": "false",
            "detectOrientation": "true",
            "scale": "true",
            "OCREngine": "2"  # OCR Engine 2 is better for non-English languages
        }

        # Call OCR.space API
        response = await client.post(
            settings.ocr_api_endpoint,
            headers={"apikey": settings.ocr_api_key},
            files=files,
            data=data
        )
        response.raise_for_status()

        result = response.json()

        # Check for errors
        if result.get("IsErroredOnProcessing", False):
            error_msg = result.get("ErrorMessage", ["Unknown error"])[0]
            logger.error(f"OCR.space error: {error_msg}")
            return [], []

        # Extract text from results
        parsed_results = result.get("ParsedResults", [])
        if not parsed_results:
            logger.warning("No parsed results from OCR.space")
            return [], []

        raw_text = parsed_results[0].get("ParsedText", "")

        if not raw_text:
            logger.warning("Empty text from OCR.space")
            return [], []

        # Extract and clean words
        words = _extract_words_from_text(raw_text)

        # OCR.space doesn't provide per-word confidence, use default
        confidences = [90.0] * len(words)

        logger.info(f"Extracted {len(words)} German words from image")
        return words, confidences

    except httpx.HTTPStatusError as e:
        logger.error(f"OCR.space API HTTP error: {e.response.status_code}")
        return [], []
    except Exception as e:
        logger.error(f"OCR word extraction error: {e}")
        return [], []


def _preprocess_image(image_data: bytes) -> bytes:
    """
    Preprocess image for better OCR accuracy while staying under 1MB limit.

    Args:
        image_data: Original image bytes

    Returns:
        Preprocessed image bytes (< 1MB)
    """
    MAX_FILE_SIZE = 1024 * 1024  # 1MB in bytes

    try:
        # Check original size
        original_size = len(image_data)
        logger.info(f"Original image size: {original_size / 1024:.1f} KB")

        # Open image from bytes
        image = Image.open(BytesIO(image_data))

        # Convert to RGB (OCR.space works better with RGB)
        if image.mode != 'RGB':
            # If image has transparency, paste on white background
            if image.mode == 'RGBA':
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])
                image = background
            else:
                image = image.convert('RGB')

        # Start with reasonable dimensions
        max_dimension = 1600  # Reduced from 2000 to keep file size down
        width, height = image.size

        # Resize if too large
        if width > max_dimension or height > max_dimension:
            scale_factor = max_dimension / max(width, height)
            new_size = (int(width * scale_factor), int(height * scale_factor))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            logger.info(f"Resized image from {width}x{height} to {new_size[0]}x{new_size[1]}")

        # Try with JPEG first (better compression than PNG)
        output = BytesIO()
        image.save(output, format='JPEG', quality=85, optimize=True)
        processed_data = output.getvalue()
        processed_size = len(processed_data)

        logger.info(f"Processed image size: {processed_size / 1024:.1f} KB")

        # If still too large, progressively reduce quality
        quality = 85
        while processed_size > MAX_FILE_SIZE and quality > 50:
            quality -= 10
            output = BytesIO()
            image.save(output, format='JPEG', quality=quality, optimize=True)
            processed_data = output.getvalue()
            processed_size = len(processed_data)
            logger.info(f"Reduced quality to {quality}, size now: {processed_size / 1024:.1f} KB")

        # If still too large, reduce dimensions
        if processed_size > MAX_FILE_SIZE:
            current_width, current_height = image.size
            scale = 0.8  # Reduce by 20% each iteration

            while processed_size > MAX_FILE_SIZE and current_width > 500:
                new_width = int(current_width * scale)
                new_height = int(current_height * scale)
                resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

                output = BytesIO()
                resized_image.save(output, format='JPEG', quality=75, optimize=True)
                processed_data = output.getvalue()
                processed_size = len(processed_data)

                current_width, current_height = new_width, new_height
                logger.info(f"Resized to {new_width}x{new_height}, size now: {processed_size / 1024:.1f} KB")

                # Update image reference for next iteration if needed
                image = resized_image

        # Final check
        if processed_size > MAX_FILE_SIZE:
            logger.warning(f"Could not reduce image below 1MB (current: {processed_size / 1024:.1f} KB)")
            # Still return it, OCR.space will reject it with a clear error

        logger.info(f"Final image size: {processed_size / 1024:.1f} KB")
        return processed_data

    except Exception as e:
        logger.error(f"Image preprocessing failed: {e}")
        # If preprocessing fails and original is under 1MB, use it
        if len(image_data) <= MAX_FILE_SIZE:
            logger.info("Using original image")
            return image_data
        else:
            logger.error(f"Original image too large ({len(image_data) / 1024:.1f} KB) and preprocessing failed")
            raise RuntimeError("Image too large and preprocessing failed")


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
        logger.info("OCR client closed")
