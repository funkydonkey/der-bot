"""Health check HTTP server for Render.com deployment."""
import logging
from typing import Optional

from aiohttp import web

from config.settings import settings

logger = logging.getLogger(__name__)

# Global server instance
app: Optional[web.Application] = None
runner: Optional[web.AppRunner] = None


async def health_check(request: web.Request) -> web.Response:
    """Health check endpoint."""
    return web.json_response({
        "status": "healthy",
        "service": "telegram-bot",
        "environment": settings.app_env
    })


async def root_handler(request: web.Request) -> web.Response:
    """Root endpoint."""
    return web.Response(text="Telegram Bot is running")


async def start_health_server(host: str = "0.0.0.0", port: int = 10000) -> None:
    """Start health check HTTP server."""
    global app, runner

    app = web.Application()
    app.router.add_get("/", root_handler)
    app.router.add_get("/health", health_check)
    app.router.add_get("/healthz", health_check)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, host, port)
    await site.start()

    logger.info(f"✓ Health check server started on http://{host}:{port}")


async def stop_health_server() -> None:
    """Stop health check HTTP server."""
    global runner

    if runner:
        await runner.cleanup()
        logger.info("Health check server stopped")
