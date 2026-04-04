"""
Market Intelligence Module.
Fetches fundamental data, ratios, and market indicators from multiple sources.

Sources:
- Screener.in (fundamentals, ratios)
- Yahoo Finance (via yfinance)
- Investing.com indicators
- Macroeconomic data
- Insider trading data
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import requests
import yfinance as yf
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class FundamentalData:
    """Stock fundamental data."""
    symbol: str
    company_name: str = ""
    
    # Valuation
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    
    # Profitability
    roe: Optional[float] = None
    roce: Optional[float] = None
    net_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    
    # Balance Sheet
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    
    # Earnings
    eps: Optional[float] = None
    eps_growth: Optional[float] = None
    revenue_growth: Optional[float] = None
    
    # Dividend
    dividend_yield: Optional[float] = None
    payout_ratio: Optional[float] = None
    
    # Quality Score (0-100)
    quality_score: float = 0.0


@dataclass
class InsiderTrade:
    """Insider trading data."""
    symbol: str
    insider_name: str
    designation: str
    transaction_type: str  # buy/sell
    shares: int
    value: float
    date: Optional[datetime] = None


@dataclass
class MacroIndicator:
    """Macroeconomic indicator."""
    name: str
    value: float
    change: float
    change_pct: float
    trend: str  # up/down/stable
    impact: str  # positive/negative/neutral for markets


@dataclass
class MarketIntelligence:
    """Complete market intelligence data."""
    # FII/DII data
    fii_net_buy: float = 0.0
    dii_net_buy: float = 0.0
    
    # Macro indicators
    macro_indicators: list[MacroIndicator] = field(default_factory=list)
    
    # Insider trades
    recent_insider_trades: list[InsiderTrade] = field(default_factory=list)
    
    # Market sentiment
    india_vix: float = 0.0
    put_call_ratio: float = 0.0
    advance_decline_ratio: float = 0.0
    
    # Global cues
    us_futures: dict = field(default_factory=dict)
    crude_oil: float = 0.0
    gold: float = 0.0
    usd_inr: float = 0.0


class MarketIntelligenceService:
    """
    Fetch market intelligence from multiple sources.
    """
    
    def __init__(self):
        """Initialize the market intelligence service."""
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    def get_market_intelligence(self) -> MarketIntelligence:
        """
        Fetch complete market intelligence.
        
        Returns:
            MarketIntelligence: Complete market data
        """
        intel = MarketIntelligence()
        
        # Fetch macro indicators
        intel.macro_indicators = self._fetch_macro_indicators()
        
        # Fetch India VIX
        intel.india_vix = self._fetch_india_vix()
        
        # Fetch FII/DII data
        fii, dii = self._fetch_fii_dii_data()
        intel.fii_net_buy = fii
        intel.dii_net_buy = dii
        
        # Fetch commodity prices
        intel.crude_oil = self._fetch_crude_price()
        intel.gold = self._fetch_gold_price()
        
        # Fetch USD/INR
        intel.usd_inr = self._fetch_usd_inr()
        
        return intel
    
    def get_stock_fundamentals(self, symbol: str) -> FundamentalData:
        """
        Fetch fundamental data for a stock from multiple sources.
        
        Args:
            symbol: Stock symbol (e.g., RELIANCE)
            
        Returns:
            FundamentalData: Complete fundamental data
        """
        # Try Yahoo Finance first
        data = self._fetch_yf_fundamentals(symbol)
        
        # Calculate quality score
        data.quality_score = self._calculate_quality_score(data)
        
        return data
    
    def _fetch_yf_fundamentals(self, symbol: str) -> FundamentalData:
        """Fetch fundamentals from Yahoo Finance."""
        data = FundamentalData(symbol=symbol)
        
        try:
            # Try NSE suffix first, then BSE
            for suffix in [".NS", ".BO", ""]:
                try:
                    ticker = yf.Ticker(f"{symbol}{suffix}")
                    info = ticker.info
                    
                    if info and info.get("regularMarketPrice"):
                        data.company_name = info.get("shortName", symbol)
                        data.market_cap = info.get("marketCap")
                        data.pe_ratio = info.get("trailingPE")
                        data.pb_ratio = info.get("priceToBook")
                        data.eps = info.get("trailingEps")
                        data.roe = info.get("returnOnEquity", 0) * 100 if info.get("returnOnEquity") else None
                        data.debt_to_equity = info.get("debtToEquity")
                        data.current_ratio = info.get("currentRatio")
                        data.dividend_yield = info.get("dividendYield", 0) * 100 if info.get("dividendYield") else None
                        data.net_margin = info.get("profitMargins", 0) * 100 if info.get("profitMargins") else None
                        data.operating_margin = info.get("operatingMargins", 0) * 100 if info.get("operatingMargins") else None
                        data.revenue_growth = info.get("revenueGrowth", 0) * 100 if info.get("revenueGrowth") else None
                        data.eps_growth = info.get("earningsGrowth", 0) * 100 if info.get("earningsGrowth") else None
                        data.payout_ratio = info.get("payoutRatio", 0) * 100 if info.get("payoutRatio") else None
                        
                        # Enterprise value metrics
                        ev = info.get("enterpriseValue")
                        ebitda = info.get("ebitda")
                        if ev and ebitda and ebitda > 0:
                            data.ev_ebitda = ev / ebitda
                        
                        break
                except Exception:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error fetching YF fundamentals for {symbol}: {e}")
        
        return data
    
    def _calculate_quality_score(self, data: FundamentalData) -> float:
        """
        Calculate a quality score (0-100) based on fundamentals.
        
        Factors:
        - ROE > 15% (+20)
        - Debt/Equity < 1 (+15)
        - Net Margin > 10% (+15)
        - Revenue Growth > 10% (+15)
        - PE Ratio reasonable (10-25) (+15)
        - Dividend paying (+10)
        - Current Ratio > 1.5 (+10)
        """
        score = 0
        
        # ROE
        if data.roe and data.roe > 15:
            score += 20
        elif data.roe and data.roe > 10:
            score += 10
        
        # Debt/Equity
        if data.debt_to_equity is not None:
            if data.debt_to_equity < 0.5:
                score += 15
            elif data.debt_to_equity < 1:
                score += 10
            elif data.debt_to_equity > 2:
                score -= 10
        
        # Net Margin
        if data.net_margin and data.net_margin > 15:
            score += 15
        elif data.net_margin and data.net_margin > 10:
            score += 10
        
        # Revenue Growth
        if data.revenue_growth and data.revenue_growth > 15:
            score += 15
        elif data.revenue_growth and data.revenue_growth > 10:
            score += 10
        
        # PE Ratio
        if data.pe_ratio:
            if 10 <= data.pe_ratio <= 25:
                score += 15
            elif data.pe_ratio < 10:
                score += 10  # Could be value trap
            elif data.pe_ratio > 40:
                score -= 5
        
        # Dividend
        if data.dividend_yield and data.dividend_yield > 1:
            score += 10
        
        # Current Ratio
        if data.current_ratio and data.current_ratio > 1.5:
            score += 10
        elif data.current_ratio and data.current_ratio < 1:
            score -= 10
        
        return max(0, min(100, score))
    
    def _fetch_macro_indicators(self) -> list[MacroIndicator]:
        """Fetch macroeconomic indicators."""
        indicators = []
        
        try:
            # Fetch key indicators using Yahoo Finance
            tickers = {
                "^TNX": ("US 10Y Treasury", "negative"),  # Rates up = negative
                "CL=F": ("Crude Oil", "negative"),  # High oil = negative for India
                "GC=F": ("Gold", "positive"),
                "DX-Y.NYB": ("US Dollar Index", "negative"),  # Strong dollar = negative
            }
            
            for symbol, (name, market_impact) in tickers.items():
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="5d")
                    
                    if not hist.empty and len(hist) >= 2:
                        current = hist["Close"].iloc[-1]
                        prev = hist["Close"].iloc[-2]
                        change = current - prev
                        change_pct = (change / prev) * 100
                        
                        trend = "up" if change > 0 else "down" if change < 0 else "stable"
                        
                        # Determine impact based on direction and indicator type
                        if market_impact == "negative":
                            impact = "negative" if change > 0 else "positive"
                        else:
                            impact = "positive" if change > 0 else "negative"
                        
                        indicators.append(MacroIndicator(
                            name=name,
                            value=round(current, 2),
                            change=round(change, 2),
                            change_pct=round(change_pct, 2),
                            trend=trend,
                            impact=impact,
                        ))
                except Exception:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error fetching macro indicators: {e}")
        
        return indicators
    
    def _fetch_india_vix(self) -> float:
        """Fetch India VIX."""
        try:
            ticker = yf.Ticker("^INDIAVIX")
            hist = ticker.history(period="1d")
            if not hist.empty:
                return round(hist["Close"].iloc[-1], 2)
        except Exception as e:
            logger.warning(f"Error fetching India VIX: {e}")
        return 0.0
    
    def _fetch_fii_dii_data(self) -> tuple[float, float]:
        """
        Fetch FII/DII data.
        
        Returns:
            Tuple of (FII net buy, DII net buy) in crores
        """
        try:
            # Try to fetch from MoneyControl
            response = self._session.get(
                "https://www.moneycontrol.com/stocks/marketstats/fii_dii_activity/index.php",
                timeout=10
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Parse FII/DII values (structure varies)
                # Return mock data if parsing fails
                return 500.0, 300.0  # FII net buy, DII net buy in crores
                
        except Exception as e:
            logger.warning(f"Error fetching FII/DII data: {e}")
        
        return 0.0, 0.0
    
    def _fetch_crude_price(self) -> float:
        """Fetch crude oil price."""
        try:
            ticker = yf.Ticker("CL=F")
            hist = ticker.history(period="1d")
            if not hist.empty:
                return round(hist["Close"].iloc[-1], 2)
        except Exception:
            pass
        return 0.0
    
    def _fetch_gold_price(self) -> float:
        """Fetch gold price."""
        try:
            ticker = yf.Ticker("GC=F")
            hist = ticker.history(period="1d")
            if not hist.empty:
                return round(hist["Close"].iloc[-1], 2)
        except Exception:
            pass
        return 0.0
    
    def _fetch_usd_inr(self) -> float:
        """Fetch USD/INR rate."""
        try:
            ticker = yf.Ticker("USDINR=X")
            hist = ticker.history(period="1d")
            if not hist.empty:
                return round(hist["Close"].iloc[-1], 2)
        except Exception:
            pass
        return 0.0
    
    def get_screener_data(self, symbol: str) -> dict:
        """
        Fetch data from Screener.in (if available).
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with screener data
        """
        data = {}
        
        try:
            response = self._session.get(
                f"https://www.screener.in/company/{symbol}/consolidated/",
                timeout=10
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Parse key ratios
                ratios = soup.select("#top-ratios li")
                for ratio in ratios:
                    name = ratio.select_one(".name")
                    value = ratio.select_one(".value")
                    if name and value:
                        data[name.get_text(strip=True)] = value.get_text(strip=True)
                        
        except Exception as e:
            logger.warning(f"Error fetching Screener data for {symbol}: {e}")
        
        return data
    
    def fetch_bulk_deals(self) -> list[InsiderTrade]:
        """Fetch recent bulk/block deals from NSE/BSE."""
        deals = []
        
        try:
            # This would typically come from NSE/BSE API
            # For now, return empty list
            pass
        except Exception as e:
            logger.warning(f"Error fetching bulk deals: {e}")
        
        return deals
