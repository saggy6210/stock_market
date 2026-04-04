"""
API Routes.
Defines the REST API endpoints for the stock market service.
"""

import os
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.config import settings
from app.notification.emailer import EmailNotifier
from app.services.stock_service import StockService

router = APIRouter()

# Singleton service instance
_service = None


def get_service() -> StockService:
    """Get or create the stock service singleton."""
    global _service
    if _service is None:
        _service = StockService()
    return _service


@router.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "name": "Stock Market Screener API",
        "version": "1.0.0",
        "endpoints": {
            "/docs": "Interactive API documentation",
            "/health": "Health check",
            "/run": "Run full daily scan",
            "/buy-signals": "Get top buy signals",
            "/sell-signals": "Get top sell signals",
            "/analyze-portfolio": "Upload CSV to analyze portfolio (POST)",
            "/portfolio-insights": "Run portfolio analysis with insights (GET)",
            "/portfolio-last": "Get last portfolio insights",
            "/report": "Get last generated report",
            "/test-email": "Send test email",
        }
    }


@router.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/test-email")
def test_email():
    """Send a test email to verify SMTP configuration."""
    notifier = EmailNotifier(
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_user=settings.smtp_user,
        smtp_password=settings.smtp_password,
        from_email=settings.email_from,
        to_emails=settings.email_to,
    )
    
    success = notifier.send(
        subject="Stock Market App - Test Email",
        body="This is a test email from the Stock Market application.",
    )
    
    return {
        "success": success,
        "message": "Test email sent" if success else "Failed to send email"
    }


@router.get("/run")
def run_daily_scan():
    """
    Run the daily market scan.
    
    Returns buy signals, sell signals, and recovery candidates.
    """
    service = get_service()
    report = service.run_daily_scan(notify=True)
    
    return {
        "date": report.date,
        "market_status": report.market_status,
        "total_stocks_analyzed": report.total_stocks_analyzed,
        "buy_signals": [
            {
                "symbol": r.symbol,
                "company": r.company_name,
                "price": r.current_price,
                "target": r.target_price,
                "signal": r.signal.value,
                "confidence": r.confidence,
                "reasons": r.reasons,
            }
            for r in report.buy_signals
        ],
        "sell_signals": [
            {
                "symbol": r.symbol,
                "company": r.company_name,
                "price": r.current_price,
                "signal": r.signal.value,
                "reasons": r.reasons,
            }
            for r in report.sell_signals
        ],
        "recovery_candidates": [
            {
                "symbol": r.symbol,
                "company": r.company_name,
                "price": r.current_price,
                "decline_from_peak": r.decline_from_peak_pct,
                "recovery_from_low": r.recovery_from_low_pct,
                "reasons": r.reasons,
            }
            for r in report.recovery_candidates
        ],
    }


@router.get("/buy-signals")
def get_buy_signals(top_n: int = 10):
    """Get top buy signals."""
    service = get_service()
    signals = service.get_buy_signals(top_n)
    
    return {
        "count": len(signals),
        "signals": [
            {
                "symbol": r.symbol,
                "company": r.company_name,
                "sector": r.sector,
                "segment": r.segment,
                "price": r.current_price,
                "target": r.target_price,
                "stop_loss": r.stop_loss,
                "expected_return": r.expected_return,
                "signal": r.signal.value,
                "confidence": r.confidence,
                "risk": r.risk_level.value,
                "rsi": r.rsi,
                "trend": r.trend.value if r.trend else None,
                "reasons": r.reasons,
            }
            for r in signals
        ],
    }


@router.get("/sell-signals")
def get_sell_signals(top_n: int = 10):
    """Get top sell signals."""
    service = get_service()
    signals = service.get_sell_signals(top_n)
    
    return {
        "count": len(signals),
        "signals": [
            {
                "symbol": r.symbol,
                "company": r.company_name,
                "price": r.current_price,
                "signal": r.signal.value,
                "reasons": r.reasons,
            }
            for r in signals
        ],
    }


@router.post("/analyze-portfolio")
async def analyze_portfolio(file: UploadFile = File(...)):
    """
    Analyze portfolio from uploaded CSV file.
    
    Expected CSV columns:
    - Symbol (stock symbol)
    - Quantity
    - Avg_Cost (purchase price)
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        service = get_service()
        report = service.analyze_portfolio(tmp_path)
        
        return {
            "date": report.date,
            "total_holdings": len(report.portfolio_analysis),
            "holdings": [
                {
                    "symbol": h.symbol,
                    "quantity": h.quantity,
                    "avg_cost": h.avg_cost,
                    "current_price": h.current_price,
                    "investment": h.investment,
                    "current_value": h.current_value,
                    "pnl": h.pnl,
                    "pnl_pct": h.pnl_pct,
                    "recommendation": {
                        "signal": h.recommendation.signal.value,
                        "confidence": h.recommendation.confidence,
                        "target": h.recommendation.target_price,
                        "reasons": h.recommendation.reasons,
                    } if h.recommendation else None,
                }
                for h in report.portfolio_analysis
            ],
        }
    finally:
        # Clean up temp file
        os.unlink(tmp_path)


@router.get("/report")
def get_last_report():
    """Get the last generated report."""
    service = get_service()
    report = service.get_last_report()
    
    if not report:
        return {"message": "No report available. Run /run first."}
    
    return {
        "date": report.date,
        "market_status": report.market_status,
        "total_stocks_analyzed": report.total_stocks_analyzed,
        "strong_buys": report.strong_buys,
        "strong_sells": report.strong_sells,
        "buy_signals_count": len(report.buy_signals),
        "sell_signals_count": len(report.sell_signals),
        "recovery_candidates_count": len(report.recovery_candidates),
    }


@router.get("/portfolio-insights")
def run_portfolio_insights(send_email: bool = True):
    """
    Run portfolio analysis and generate insights.
    
    Analyzes holdings.csv and provides:
    - Portfolio summary (value, P/L, allocation, risk flags)
    - Top 20 stock movement predictions
    - Relevant news for portfolio stocks
    - Buy/Hold/Sell signals for each stock
    
    Args:
        send_email: Whether to send email notification (default: True)
    """
    service = get_service()
    insights = service.run_portfolio_analysis(notify=send_email)
    
    return {
        "date": insights.date,
        "summary": {
            "total_investment": insights.summary.total_investment,
            "current_value": insights.summary.current_value,
            "total_pnl": insights.summary.total_pnl,
            "total_pnl_pct": insights.summary.total_pnl_pct,
            "day_change_pct": insights.summary.day_change_pct,
            "total_stocks": insights.summary.total_stocks,
            "profitable_stocks": insights.summary.profitable_stocks,
            "loss_making_stocks": insights.summary.loss_making_stocks,
            "overall_risk_level": insights.summary.overall_risk_level.value,
            "risk_flags": insights.summary.risk_flags.get_flags(),
        },
        "signals": {
            "aggressive_buy": [
                {"symbol": h.symbol, "pnl_pct": h.pnl_pct, "score": h.fundamental_score, "reasons": h.reasons}
                for h in insights.aggressive_buy_stocks[:5]
            ],
            "buy_on_dip": [h.symbol for h in insights.buy_on_dip_stocks[:5]],
            "hold": [h.symbol for h in insights.hold_stocks[:10]],
            "reduce": [h.symbol for h in insights.reduce_stocks[:5]],
            "exit": [
                {"symbol": h.symbol, "pnl_pct": h.pnl_pct, "score": h.fundamental_score, "reasons": h.reasons}
                for h in insights.exit_stocks
            ],
        },
        "predictions": [
            {
                "symbol": h.symbol,
                "direction": h.predicted_direction,
                "confidence": h.predicted_confidence,
                "reason": h.prediction_reason,
            }
            for h in insights.predictions[:10]
        ],
        "market_outlook": insights.market_outlook,
        "strategy_notes": insights.strategy_notes,
        "email_sent": send_email,
    }


@router.get("/portfolio-last")
def get_last_portfolio_insights():
    """Get the last generated portfolio insights."""
    service = get_service()
    insights = service.get_last_portfolio_insights()
    
    if not insights:
        return {"message": "No portfolio insights available. Run /portfolio-insights first."}
    
    return {
        "date": insights.date,
        "total_stocks": insights.summary.total_stocks,
        "total_pnl_pct": insights.summary.total_pnl_pct,
        "aggressive_buy_count": len(insights.aggressive_buy_stocks),
        "exit_count": len(insights.exit_stocks),
    }
