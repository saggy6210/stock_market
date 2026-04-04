"""
FastAPI application entry point.
Sets up the app with async lifespan management for scheduler.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router, get_service
from app.config import settings
from app.utils.logging import configure_logging
from app.scheduler.jobs import create_scheduler, start_scheduler, stop_scheduler, set_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async lifespan context manager for startup/shutdown."""
    configure_logging(settings.log_level)
    logger.info(f"Starting {settings.app_name}...")
    
    # Start scheduler if enabled
    scheduler = None
    if settings.enable_scheduler:
        service = get_service()
        scheduler = create_scheduler(service)
        set_scheduler(scheduler)
        start_scheduler(scheduler)
        logger.info("Scheduler started")
    
    yield
    
    # Stop scheduler on shutdown
    if scheduler:
        stop_scheduler(scheduler)
        logger.info("Scheduler stopped")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: The configured application instance.
    """
    application = FastAPI(
        title=settings.app_name,
        description="Stock Market Screening and Analysis Service",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.include_router(router)
    return application


# Application instance
app = create_app()
