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
    
    # Single daily job at 6:55 AM IST - runs all tasks in sequence
    scheduler.add_job(
        func=lambda: _run_complete_daily_analysis(service),
        trigger=CronTrigger(
            hour=6,
            minute=55,
            timezone="Asia/Kolkata",
        ),
        id="daily-complete-analysis",
        name="Daily Complete Analysis (Dashboard + Scan + Portfolio)",
        replace_existing=True,
    )
    
    logger.info(
        "Scheduler configured: Complete daily analysis at 06:55 AM IST"
    )
    
    return scheduler


def _run_complete_daily_analysis(service) -> None:
    """
    Single job that runs all daily tasks in sequence:
    1. Dashboard data generation
    2. Daily market scan
    3. Portfolio analysis with email
    
    Args:
        service: StockService instance
    """
    logger.info(f"Starting complete daily analysis at {datetime.now()}")
    
    # Step 1: Generate dashboard data
    try:
        logger.info("Step 1/3: Generating dashboard data...")
        from app.analysis.dashboard_pipeline import run_pipeline
        data = run_pipeline()
        logger.info(
            f"Dashboard data generated: {len(data.get('indices', {}))} indices, "
            f"{len(data.get('commodities', {}))} commodities"
        )
    except Exception as e:
        logger.error(f"Dashboard generation failed: {e}", exc_info=True)
    
    # Step 2: Run daily market scan (without notification - portfolio will send combined email)
    try:
        logger.info("Step 2/3: Running daily market scan...")
        report = service.run_daily_scan(notify=False)
        logger.info(
            f"Daily scan completed: {len(report.buy_signals)} buy signals, "
            f"{len(report.sell_signals)} sell signals"
        )
    except Exception as e:
        logger.error(f"Daily scan failed: {e}", exc_info=True)
    
    # Step 3: Run portfolio analysis with email notification
    try:
        logger.info("Step 3/3: Running portfolio analysis...")
        insights = service.run_portfolio_analysis(notify=True)
        logger.info(
            f"Portfolio analysis completed: {len(insights.holdings)} holdings, "
            f"P/L: {insights.summary.total_pnl_pct:.2f}%"
        )
    except Exception as e:
        logger.error(f"Portfolio analysis failed: {e}", exc_info=True)
    
    logger.info(f"Complete daily analysis finished at {datetime.now()}")


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
