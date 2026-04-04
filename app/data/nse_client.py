"""
NSE Client.
Handles fetching stock data from NSE (National Stock Exchange) APIs.
"""

import logging
import time
from typing import Optional
import requests
import yfinance as yf
import pandas as pd

from app.data.models import StockSnapshot

logger = logging.getLogger(__name__)


class NSEClient:
    """Client for fetching data from NSE APIs."""
    
    BASE_URL = "https://www.nseindia.com"
    
    # Index URLs for different market caps
    INDICES = {
        "NIFTY 50": "NIFTY 50",
        "NIFTY NEXT 50": "NIFTY NEXT 50",
        "NIFTY 100": "NIFTY 100",
        "NIFTY 200": "NIFTY 200",
        "NIFTY 500": "NIFTY 500",
        "NIFTY MIDCAP 50": "NIFTY MIDCAP 50",
        "NIFTY MIDCAP 100": "NIFTY MIDCAP 100",
        "NIFTY SMALLCAP 50": "NIFTY SMALLCAP 50",
        "NIFTY SMALLCAP 100": "NIFTY SMALLCAP 100",
        "NIFTY SMALLCAP 250": "NIFTY SMALLCAP 250",
        "NIFTY MICROCAP 250": "NIFTY MICROCAP 250",
    }
    
    def __init__(self):
        """Initialize the NSE client."""
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/",
        })
        self._cookies_set = False
    
    def _set_cookies(self):
        """Set cookies by visiting the main page."""
        if self._cookies_set:
            return
        try:
            self._session.get(self.BASE_URL, timeout=10)
            self._cookies_set = True
        except Exception as e:
            logger.warning(f"Failed to set cookies: {e}")
    
    def _make_request(self, url: str, retries: int = 3) -> Optional[dict]:
        """Make HTTP request with retry logic."""
        self._set_cookies()
        
        for attempt in range(retries):
            try:
                response = self._session.get(url, timeout=15)
                if response.status_code == 200:
                    return response.json()
                logger.warning(f"NSE API returned {response.status_code}")
            except Exception as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                time.sleep(2 ** attempt)
        
        return None
    
    def fetch_index_stocks(self, index_name: str) -> list[dict]:
        """
        Fetch stocks from a specific index.
        
        Args:
            index_name: Name of the index (e.g., "NIFTY 50")
            
        Returns:
            list: List of stock data dictionaries
        """
        url = f"{self.BASE_URL}/api/equity-stockIndices?index={index_name.replace(' ', '%20')}"
        data = self._make_request(url)
        
        if data and "data" in data:
            return data["data"]
        return []
    
    def fetch_all_stocks(self, include_micro: bool = True) -> list[StockSnapshot]:
        """
        Fetch all stocks from multiple indices.
        
        Args:
            include_micro: Include micro cap stocks
            
        Returns:
            list: List of StockSnapshot objects
        """
        all_stocks = {}
        
        indices_to_fetch = [
            ("NIFTY 500", "Large/Mid Cap"),
            ("NIFTY SMALLCAP 250", "Small Cap"),
        ]
        
        if include_micro:
            indices_to_fetch.append(("NIFTY MICROCAP 250", "Micro Cap"))
        
        for index_name, segment in indices_to_fetch:
            logger.info(f"Fetching {index_name}...")
            stocks = self.fetch_index_stocks(index_name)
            
            for stock in stocks:
                symbol = stock.get("symbol", "")
                if not symbol or symbol in all_stocks:
                    continue
                
                # Determine segment based on index
                if "LARGE" in index_name.upper() or index_name in ["NIFTY 50", "NIFTY 100"]:
                    cap_segment = "Large Cap"
                elif "MID" in index_name.upper():
                    cap_segment = "Mid Cap"
                elif "MICRO" in index_name.upper():
                    cap_segment = "Micro Cap"
                elif "SMALL" in index_name.upper():
                    cap_segment = "Small Cap"
                else:
                    cap_segment = segment
                
                all_stocks[symbol] = StockSnapshot(
                    symbol=symbol,
                    company_name=stock.get("companyName", symbol),
                    sector=stock.get("industry", ""),
                    segment=cap_segment,
                    price=self._safe_float(stock.get("lastPrice")),
                    open_price=self._safe_float(stock.get("open")),
                    high=self._safe_float(stock.get("dayHigh")),
                    low=self._safe_float(stock.get("dayLow")),
                    prev_close=self._safe_float(stock.get("previousClose")),
                    change=self._safe_float(stock.get("change")),
                    change_pct=self._safe_float(stock.get("pChange")),
                    fifty_two_week_high=self._safe_float(stock.get("yearHigh")),
                    fifty_two_week_low=self._safe_float(stock.get("yearLow")),
                    pe_ratio=self._safe_float(stock.get("pe")),
                )
            
            time.sleep(1)  # Rate limiting
        
        logger.info(f"Fetched {len(all_stocks)} unique stocks")
        return list(all_stocks.values())
    
    def fetch_stock_history(
        self,
        symbol: str,
        period: str = "6mo",
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical data for a stock using yfinance.
        
        Args:
            symbol: Stock symbol
            period: Time period (1mo, 3mo, 6mo, 1y, etc.)
            
        Returns:
            DataFrame: Historical price data
        """
        try:
            # Try NSE symbol first, then BSE
            for suffix in [".NS", ".BO"]:
                ticker = yf.Ticker(f"{symbol}{suffix}")
                df = ticker.history(period=period)
                if not df.empty:
                    return df
        except Exception as e:
            logger.warning(f"Failed to fetch history for {symbol}: {e}")
        
        return None
    
    def fetch_stock_info(self, symbol: str) -> Optional[dict]:
        """
        Fetch detailed info for a stock using yfinance.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            dict: Stock info
        """
        try:
            for suffix in [".NS", ".BO"]:
                ticker = yf.Ticker(f"{symbol}{suffix}")
                info = ticker.info
                if info and info.get("regularMarketPrice"):
                    return info
        except Exception as e:
            logger.warning(f"Failed to fetch info for {symbol}: {e}")
        
        return None
    
    def is_market_open(self) -> bool:
        """Check if market is currently open."""
        url = f"{self.BASE_URL}/api/marketStatus"
        data = self._make_request(url)
        
        if data and "marketState" in data:
            for market in data["marketState"]:
                if market.get("market") == "Capital Market":
                    return market.get("marketStatus") == "Open"
        
        return False
    
    def _safe_float(self, value, default: float = 0.0) -> float:
        """Safely convert value to float."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
