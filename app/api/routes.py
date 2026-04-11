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


@router.get("/stock/{symbol}")
def get_stock_price(symbol: str):
    """
    Get current stock price for a symbol using NSE direct API.
    
    Args:
        symbol: Stock symbol (e.g., HDFCBANK, RELIANCE)
    """
    from app.data.nse_client import NSEClient
    
    # Remove .NS suffix if present
    clean_symbol = symbol.replace(".NS", "").replace(".BO", "").upper()
    
    nse = NSEClient()
    
    try:
        # Try to get quote directly from NSE
        url = f"{nse.BASE_URL}/api/quote-equity?symbol={clean_symbol}"
        nse._set_cookies()
        response = nse._session.get(url, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            price_info = data.get("priceInfo", {})
            
            return {
                "symbol": clean_symbol,
                "price": price_info.get("lastPrice", 0),
                "change": price_info.get("change", 0),
                "change_pct": price_info.get("pChange", 0),
                "open": price_info.get("open", 0),
                "high": price_info.get("intraDayHighLow", {}).get("max", 0),
                "low": price_info.get("intraDayHighLow", {}).get("min", 0),
                "prev_close": price_info.get("previousClose", 0),
                "source": "NSE"
            }
    except Exception as e:
        pass
    
    # Fallback to yfinance
    try:
        import yfinance as yf
        ticker = yf.Ticker(f"{clean_symbol}.NS")
        hist = ticker.history(period="1d")
        
        if not hist.empty:
            return {
                "symbol": clean_symbol,
                "price": round(float(hist['Close'].iloc[-1]), 2),
                "source": "Yahoo Finance"
            }
    except:
        pass
    
    raise HTTPException(status_code=404, detail=f"No data found for {symbol}")


@router.get("/nse-prices")
def get_nse_prices(symbols: str = None):
    """
    Get real-time prices for multiple stocks from NSE.
    
    Args:
        symbols: Comma-separated list of symbols (e.g., HDFCBANK,RELIANCE,TCS)
                If not provided, returns Nifty 50 stocks
    """
    from app.data.nse_client import NSEClient
    
    nse = NSEClient()
    
    if symbols:
        # Fetch specific symbols
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        results = {}
        
        for symbol in symbol_list:
            try:
                url = f"{nse.BASE_URL}/api/quote-equity?symbol={symbol}"
                nse._set_cookies()
                response = nse._session.get(url, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    price_info = data.get("priceInfo", {})
                    
                    results[symbol] = {
                        "price": price_info.get("lastPrice", 0),
                        "change": price_info.get("change", 0),
                        "change_pct": price_info.get("pChange", 0),
                    }
            except:
                results[symbol] = {"error": "Failed to fetch"}
        
        return {"stocks": results, "source": "NSE Direct"}
    else:
        # Fetch Nifty 50 stocks
        stocks = nse.fetch_index_stocks("NIFTY 50")
        results = {}
        
        for stock in stocks:
            symbol = stock.get("symbol", "")
            if symbol:
                results[symbol] = {
                    "price": stock.get("lastPrice", 0),
                    "change": stock.get("change", 0),
                    "change_pct": stock.get("pChange", 0),
                    "open": stock.get("open", 0),
                    "high": stock.get("dayHigh", 0),
                    "low": stock.get("dayLow", 0),
                }
        
        return {"stocks": results, "count": len(results), "source": "NSE Direct"}


@router.get("/dashboard-data")
def get_dashboard_data():
    """
    Get complete dashboard data including:
    - Market indices (real-time from NSE)
    - Commodity prices
    - All stock prices for recommendations
    """
    from app.data.nse_client import NSEClient
    from datetime import datetime
    import yfinance as yf
    
    nse = NSEClient()
    
    def fetch_nse_index(index_name):
        """Fetch index data from NSE."""
        try:
            stocks = nse.fetch_index_stocks(index_name)
            if stocks:
                # First item is usually the index itself
                for item in stocks:
                    if item.get("symbol") == index_name.replace(" ", ""):
                        return {
                            "name": index_name,
                            "value": item.get("lastPrice", 0),
                            "change": item.get("change", 0),
                            "change_pct": item.get("pChange", 0),
                            "is_positive": item.get("change", 0) >= 0
                        }
        except:
            pass
        return None
    
    def fetch_yf_index(symbol, name):
        """Fallback to Yahoo Finance for indices."""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            if hist.empty or len(hist) < 2:
                return None
            
            last_close = float(hist['Close'].iloc[-1])
            prev_close = float(hist['Close'].iloc[-2])
            change = last_close - prev_close
            change_pct = (change / prev_close) * 100
            
            return {
                "name": name,
                "value": round(last_close, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "is_positive": change >= 0
            }
        except:
            return None
    
    # Fetch Indian indices from NSE
    indices = {
        "nifty": fetch_nse_index("NIFTY 50") or fetch_yf_index("^NSEI", "Nifty 50"),
        "nifty_bank": fetch_nse_index("NIFTY BANK") or fetch_yf_index("^NSEBANK", "Nifty Bank"),
        "nifty_it": fetch_nse_index("NIFTY IT") or fetch_yf_index("^CNXIT", "Nifty IT"),
    }
    
    # US indices from Yahoo Finance
    indices["dow_jones"] = fetch_yf_index("^DJI", "Dow Jones")
    indices["nasdaq"] = fetch_yf_index("^IXIC", "NASDAQ")
    indices["sensex"] = fetch_yf_index("^BSESN", "Sensex")
    indices["india_vix"] = fetch_yf_index("^INDIAVIX", "India VIX")
    indices["usd_inr"] = fetch_yf_index("USDINR=X", "USD/INR")
    
    # Fetch commodities from Yahoo Finance
    commodities = {
        "gold": fetch_yf_index("GC=F", "Gold"),
        "silver": fetch_yf_index("SI=F", "Silver"),
        "copper": fetch_yf_index("HG=F", "Copper"),
        "crude_oil": fetch_yf_index("CL=F", "Crude Oil"),
        "natural_gas": fetch_yf_index("NG=F", "Natural Gas"),
    }
    
    # Fetch all recommendation stocks from NSE
    rec_symbols = [
        "HDFCBANK", "RELIANCE", "INFY", "TCS", "BAJFINANCE",
        "BHARTIARTL", "ICICIBANK", "MARUTI", "TITAN", "LT",
        "PAYTM", "ZOMATO", "WIPRO", "TATASTEEL", "HINDPETRO",
        "BPCL", "IOC", "VEDL", "SAIL", "COALINDIA"
    ]
    
    stock_prices = {}
    for symbol in rec_symbols:
        try:
            url = f"{nse.BASE_URL}/api/quote-equity?symbol={symbol}"
            nse._set_cookies()
            response = nse._session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                price_info = data.get("priceInfo", {})
                stock_prices[symbol.lower()] = {
                    "price": price_info.get("lastPrice", 0),
                    "change_pct": price_info.get("pChange", 0),
                }
        except:
            pass
    
    return {
        "generated_at": datetime.now().isoformat(),
        "indices": indices,
        "commodities": commodities,
        "stock_prices": stock_prices,
        "source": "NSE Direct + Yahoo Finance"
    }


@router.get("/screener-data")
def get_screener_data(period: str = "1m"):
    """
    Get top fallen stocks data.
    
    Args:
        period: Time period - 1m (1 month), 3m, 6m, 1y
    """
    from app.data.nse_client import NSEClient
    import yfinance as yf
    from datetime import datetime, timedelta
    
    nse = NSEClient()
    
    # Calculate date range
    period_map = {
        "1m": 30,
        "3m": 90,
        "6m": 180,
        "1y": 365
    }
    days = period_map.get(period, 30)
    start_date = datetime.now() - timedelta(days=days)
    
    # Get Nifty 500 stocks
    all_stocks = nse.fetch_index_stocks("NIFTY 500")
    
    fallen_stocks = []
    
    for stock in all_stocks[:100]:  # Limit to top 100 for performance
        symbol = stock.get("symbol", "")
        current_price = stock.get("lastPrice", 0)
        
        if not symbol or not current_price:
            continue
        
        try:
            # Fetch historical price
            ticker = yf.Ticker(f"{symbol}.NS")
            hist = ticker.history(start=start_date.strftime("%Y-%m-%d"))
            
            if not hist.empty:
                old_price = float(hist['Close'].iloc[0])
                if old_price > 0:
                    fall_pct = ((current_price - old_price) / old_price) * 100
                    
                    if fall_pct < -10:  # Only stocks with >10% fall
                        fallen_stocks.append({
                            "symbol": symbol,
                            "company": stock.get("companyName", symbol),
                            "sector": stock.get("industry", ""),
                            "old_price": round(old_price, 2),
                            "current_price": current_price,
                            "fall_pct": round(fall_pct, 2)
                        })
        except:
            continue
    
    # Sort by fall percentage
    fallen_stocks.sort(key=lambda x: x["fall_pct"])
    
    return {
        "period": period,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "stocks": fallen_stocks[:10],
        "total_found": len(fallen_stocks)
    }


@router.get("/fii-dii")
def get_fii_dii_data():
    """
    Get FII/DII activity data from NSE.
    """
    from app.data.nse_client import NSEClient
    from datetime import datetime, timedelta
    
    nse = NSEClient()
    
    # Try to fetch from NSE
    try:
        url = f"{nse.BASE_URL}/api/fiidiiTradeReact"
        nse._set_cookies()
        response = nse._session.get(url, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "data": data,
                "source": "NSE Direct"
            }
    except:
        pass
    
    # Fallback to simulated data
    today = datetime.now()
    daily_data = []
    
    for i in range(5):
        date = today - timedelta(days=i)
        if date.weekday() < 5:
            daily_data.append({
                "date": date.strftime("%d %b %Y"),
                "fii_buy": 7500 + (i * 200) + (500 if i % 2 == 0 else -200),
                "fii_sell": 9000 + (i * 150) + (300 if i % 2 == 1 else -100),
                "fii_net": -1500 - (i * 50) + (200 if i % 2 == 0 else -100),
                "dii_buy": 8500 + (i * 180) + (400 if i % 2 == 1 else -150),
                "dii_sell": 6000 + (i * 120) + (200 if i % 2 == 0 else -50),
                "dii_net": 2500 + (i * 60) + (200 if i % 2 == 1 else -100),
            })
    
    return {
        "daily": daily_data,
        "monthly": {"fii_net": -15234, "dii_net": 18567},
        "ytd": {"fii_net": -45890, "dii_net": 52345},
        "source": "Simulated Data"
    }


@router.post("/generate-dashboard-data")
def generate_dashboard_data():
    """
    Manually trigger the dashboard data generation pipeline.
    This fetches all data from various sources and generates the dashboard JSON.
    
    Can be called via:
    - POST /api/generate-dashboard-data
    - Or scheduled via cron jobs
    """
    from app.analysis.dashboard_pipeline import run_pipeline
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Dashboard data generation triggered via API")
        data = run_pipeline()
        
        return {
            "status": "success",
            "message": "Dashboard data generated successfully",
            "timestamp": data.get("timestamp"),
            "sections_generated": list(data.keys()),
            "indices_count": len(data.get("indices", {})),
            "commodities_count": len(data.get("commodities", {})),
            "screener_periods": list(data.get("screener", {}).keys())
        }
    except Exception as e:
        logger.error(f"Dashboard generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard-status")
def get_dashboard_status():
    """
    Check the status of the last generated dashboard data.
    Returns when it was last generated and basic info.
    """
    import json
    from pathlib import Path
    from datetime import datetime
    
    data_file = Path(__file__).parent.parent.parent / "market_dashboard" / "data" / "dashboard_data.json"
    
    if not data_file.exists():
        return {
            "status": "not_generated",
            "message": "Dashboard data has not been generated yet. Call POST /api/generate-dashboard-data to generate."
        }
    
    try:
        with open(data_file, "r") as f:
            data = json.load(f)
        
        timestamp = data.get("timestamp", "Unknown")
        
        return {
            "status": "available",
            "last_generated": timestamp,
            "file_path": str(data_file),
            "sections": list(data.keys()),
            "indices": list(data.get("indices", {}).keys()),
            "commodities": list(data.get("commodities", {}).keys())
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
