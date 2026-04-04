"""
FastAPI application entry point.
Sets up the app with async lifespan management for scheduler.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.config import settings
from app.utils.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async lifespan context manager for startup/shutdown."""
    configure_logging(settings.log_level)
    # TODO: Start scheduler here if enabled
    yield
    # TODO: Stop scheduler here


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: The configured application instance.
    """
    application = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
    )
    application.include_router(router)
    return application


# Application instance
app = create_app()
