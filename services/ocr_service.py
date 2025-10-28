"""MCP OCR service."""
import logging
from typing import Optional

import httpx

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


async def process_image_ocr(image_data: bytes) -> str:
    """Process image with OCR and return extracted text."""
    if client is None:
        raise RuntimeError("MCP OCR client not initialized")

    try:
        # This will need to be adjusted based on actual MCP OCR API
        response = await client.post(
            "/ocr",
            files={"image": image_data},
        )
        response.raise_for_status()

        result = response.json()
        return result.get("text", "")

    except Exception as e:
        logger.error(f"OCR processing error: {e}")
        raise


async def close_ocr_client() -> None:
    """Close OCR HTTP client."""
    global client

    if client:
        await client.aclose()
        logger.info("MCP OCR client closed")
