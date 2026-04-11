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
    
    # Add daily scan job at 7:00 AM IST, every day
    scheduler.add_job(
        func=lambda: _run_daily_scan(service),
        trigger=CronTrigger(
            hour=settings.schedule_hour,
            minute=settings.schedule_minute,
            timezone="Asia/Kolkata",
        ),
        id="daily-stock-scan",
        name="Daily Stock Market Scan",
        replace_existing=True,
    )
    
    # Add portfolio analysis job at 7:05 AM IST, every day (5 minutes after daily scan)
    scheduler.add_job(
        func=lambda: _run_portfolio_analysis(service),
        trigger=CronTrigger(
            hour=settings.schedule_hour,
            minute=settings.schedule_minute + 5,  # 5 minutes after market scan
            timezone="Asia/Kolkata",
        ),
        id="portfolio-analysis",
        name="Portfolio Analysis and Recommendations",
        replace_existing=True,
    )
    
    # Add dashboard data generation job at 6:55 AM IST (before market opens)
    scheduler.add_job(
        func=_run_dashboard_pipeline,
        trigger=CronTrigger(
            hour=6,
            minute=55,
            timezone="Asia/Kolkata",
        ),
        id="dashboard-data-generation",
        name="Dashboard Data Generation",
        replace_existing=True,
    )
    
    # Also run dashboard pipeline at 3:35 PM IST (after market closes)
    scheduler.add_job(
        func=_run_dashboard_pipeline,
        trigger=CronTrigger(
            hour=15,
            minute=35,
            timezone="Asia/Kolkata",
        ),
        id="dashboard-data-generation-eod",
        name="Dashboard Data Generation (EOD)",
        replace_existing=True,
    )
    
    logger.info(
        f"Scheduler configured: Daily scan at {settings.schedule_hour:02d}:{settings.schedule_minute:02d} IST (Daily)"
    )
    logger.info(
        f"Scheduler configured: Portfolio analysis at {settings.schedule_hour:02d}:{settings.schedule_minute + 5:02d} IST (Daily)"
    )
    logger.info(
        "Scheduler configured: Dashboard data generation at 06:55 and 15:35 IST (Daily)"
    )
    
    return scheduler


def _run_dashboard_pipeline() -> None:
    """
    Job function for dashboard data generation.
    
    Generates all data needed for the market dashboard:
    - Index prices (NIFTY, SENSEX, etc.)
    - Commodity prices
    - Screener data (fallen stocks)
    - FII/DII activity
    - Market outlook
    - Predictions
    """
    logger.info(f"Starting dashboard data pipeline at {datetime.now()}")
    
    try:
        from app.analysis.dashboard_pipeline import run_pipeline
        
        data = run_pipeline()
        
        logger.info(
            f"Dashboard data generation completed: "
            f"{len(data.get('indices', {}))} indices, "
            f"{len(data.get('commodities', {}))} commodities, "
            f"{len(data.get('screener', {}).get('feb26', []))} screener stocks"
        )
        
    except Exception as e:
        logger.error(f"Dashboard data generation failed: {e}", exc_info=True)


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


def _run_portfolio_analysis(service) -> None:
    """
    Job function for portfolio analysis.
    
    Sends a separate email with:
    - Portfolio summary and P/L
    - Stock movement predictions for portfolio holdings
    - Relevant news for portfolio stocks
    - Buy/Hold/Sell signals for each stock
    
    Args:
        service: StockService instance
    """
    logger.info(f"Starting scheduled portfolio analysis at {datetime.now()}")
    
    try:
        insights = service.run_portfolio_analysis(notify=True)
        
        logger.info(
            f"Portfolio analysis completed: "
            f"{len(insights.holdings)} holdings, "
            f"P/L: {insights.summary.total_pnl_pct:.2f}%, "
            f"Aggressive Buy: {len(insights.aggressive_buy_stocks)}, "
            f"Exit: {len(insights.exit_stocks)}"
        )
        
    except Exception as e:
        logger.error(f"Portfolio analysis failed: {e}", exc_info=True)


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
