"""
Scheduled Jobs.
APScheduler integration for automated stock scanning.
"""

import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[BackgroundScheduler] = None


def create_scheduler(service) -> BackgroundScheduler:
    """
    Create and configure the background scheduler.
    
    Args:
        service: StockService instance to use for jobs
        
    Returns:
        BackgroundScheduler: Configured scheduler instance
    """
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    
    # Add daily scan job at 9:00 AM IST, Monday to Friday
    scheduler.add_job(
        func=lambda: _run_daily_scan(service),
        trigger=CronTrigger(
            hour=settings.schedule_hour,
            minute=settings.schedule_minute,
            day_of_week="mon-fri",
            timezone="Asia/Kolkata",
        ),
        id="daily-stock-scan",
        name="Daily Stock Market Scan",
        replace_existing=True,
    )
    
    logger.info(
        f"Scheduler configured: Daily scan at {settings.schedule_hour:02d}:{settings.schedule_minute:02d} IST (Mon-Fri)"
    )
    
    return scheduler


def _run_daily_scan(service) -> None:
    """
    Job function for daily stock scan.
    
    Args:
        service: StockService instance
    """
    logger.info(f"Starting scheduled daily scan at {datetime.now()}")
    
    try:
        # Check if it's a trading day (basic check)
        # TODO: Add proper NSE/BSE holiday calendar check
        
        report = service.run_daily_scan(notify=True)
        
        logger.info(
            f"Daily scan completed: "
            f"{len(report.buy_signals)} buy signals, "
            f"{len(report.sell_signals)} sell signals"
        )
        
    except Exception as e:
        logger.error(f"Daily scan failed: {e}", exc_info=True)


def start_scheduler(scheduler: BackgroundScheduler) -> None:
    """
    Start the scheduler.
    
    Args:
        scheduler: BackgroundScheduler instance
    """
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def stop_scheduler(scheduler: BackgroundScheduler) -> None:
    """
    Stop the scheduler gracefully.
    
    Args:
        scheduler: BackgroundScheduler instance
    """
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def get_scheduler() -> Optional[BackgroundScheduler]:
    """Get the global scheduler instance."""
    return _scheduler


def set_scheduler(scheduler: BackgroundScheduler) -> None:
    """Set the global scheduler instance."""
    global _scheduler
    _scheduler = scheduler
