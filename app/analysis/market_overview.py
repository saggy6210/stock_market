"""
Market Overview.
Fetches global market indices, currency data, and determines market sentiment.
"""

import logging
from dataclasses import dataclass
from typing import Optional
import yfinance as yf

logger = logging.getLogger(__name__)


@dataclass
class MarketIndex:
    """Market index data."""
    name: str
    symbol: str
    last_close: float
    change: float
    change_pct: float
    is_up: bool


@dataclass
class MarketOverview:
    """Complete market overview data."""
    dow_jones: Optional[MarketIndex] = None
    nasdaq: Optional[MarketIndex] = None
    gift_nifty: Optional[MarketIndex] = None
    sensex: Optional[MarketIndex] = None
    nifty: Optional[MarketIndex] = None
    usd_inr: Optional[MarketIndex] = None
    market_outlook: str = "NEUTRAL"
    outlook_reason: str = ""


class MarketOverviewFetcher:
    """Fetch global market data for daily overview."""
    
    # Market index symbols
    INDICES = {
        "dow_jones": ("^DJI", "Dow Jones"),
        "nasdaq": ("^IXIC", "NASDAQ"),
        "gift_nifty": ("^NSEI", "GIFT Nifty"),  # Using Nifty as proxy
        "sensex": ("^BSESN", "Sensex"),
        "nifty": ("^NSEI", "Nifty 50"),
        "usd_inr": ("USDINR=X", "USD/INR"),
    }
    
    def __init__(self):
        """Initialize the market overview fetcher."""
        pass
    
    def get_overview(self) -> MarketOverview:
        """
        Fetch complete market overview.
        
        Returns:
            MarketOverview with all indices data
        """
        overview = MarketOverview()
        
        # Fetch each index
        overview.dow_jones = self._fetch_index("dow_jones")
        overview.nasdaq = self._fetch_index("nasdaq")
        overview.gift_nifty = self._fetch_gift_nifty()
        overview.sensex = self._fetch_index("sensex")
        overview.nifty = self._fetch_index("nifty")
        overview.usd_inr = self._fetch_index("usd_inr")
        
        # Determine market outlook
        outlook, reason = self._determine_outlook(overview)
        overview.market_outlook = outlook
        overview.outlook_reason = reason
        
        return overview
    
    def _fetch_index(self, index_key: str) -> Optional[MarketIndex]:
        """Fetch data for a single index."""
        try:
            symbol, name = self.INDICES[index_key]
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            
            if hist.empty or len(hist) < 2:
                logger.warning(f"No data for {name}")
                return None
            
            last_close = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            change = last_close - prev_close
            change_pct = (change / prev_close) * 100
            
            return MarketIndex(
                name=name,
                symbol=symbol,
                last_close=round(last_close, 2),
                change=round(change, 2),
                change_pct=round(change_pct, 2),
                is_up=change >= 0
            )
        except Exception as e:
            logger.error(f"Error fetching {index_key}: {e}")
            return None
    
    def _fetch_gift_nifty(self) -> Optional[MarketIndex]:
        """
        Fetch GIFT Nifty (SGX Nifty) data.
        Using Nifty futures as proxy since direct GIFT Nifty may not be available.
        """
        try:
            # Try SGX Nifty first
            for symbol in ["^NSEI", "NQ=F"]:  # Nifty or Nifty futures
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")
                
                if not hist.empty and len(hist) >= 2:
                    last_close = hist['Close'].iloc[-1]
                    prev_close = hist['Close'].iloc[-2]
                    change = last_close - prev_close
                    change_pct = (change / prev_close) * 100
                    
                    return MarketIndex(
                        name="GIFT Nifty",
                        symbol=symbol,
                        last_close=round(last_close, 2),
                        change=round(change, 2),
                        change_pct=round(change_pct, 2),
                        is_up=change >= 0
                    )
            return None
        except Exception as e:
            logger.error(f"Error fetching GIFT Nifty: {e}")
            return None
    
    def _determine_outlook(self, overview: MarketOverview) -> tuple[str, str]:
        """
        Determine market outlook based on global cues.
        
        Returns:
            Tuple of (outlook, reason)
        """
        bullish_signals = 0
        bearish_signals = 0
        reasons = []
        
        # Check US markets (major influence)
        if overview.dow_jones:
            if overview.dow_jones.is_up:
                bullish_signals += 2
                reasons.append(f"Dow Jones up {overview.dow_jones.change_pct:.1f}%")
            else:
                bearish_signals += 2
                reasons.append(f"Dow Jones down {abs(overview.dow_jones.change_pct):.1f}%")
        
        if overview.nasdaq:
            if overview.nasdaq.is_up:
                bullish_signals += 2
                reasons.append(f"NASDAQ up {overview.nasdaq.change_pct:.1f}%")
            else:
                bearish_signals += 2
                reasons.append(f"NASDAQ down {abs(overview.nasdaq.change_pct):.1f}%")
        
        # Check GIFT Nifty (early indicator)
        if overview.gift_nifty:
            if overview.gift_nifty.is_up:
                bullish_signals += 1
                reasons.append(f"GIFT Nifty positive")
            else:
                bearish_signals += 1
                reasons.append(f"GIFT Nifty negative")
        
        # Check USD/INR (rupee strength)
        if overview.usd_inr:
            # Lower USD/INR means stronger rupee (bullish)
            if not overview.usd_inr.is_up:  # USD down = INR strong
                bullish_signals += 1
                reasons.append("INR strengthening")
            else:
                bearish_signals += 1
                reasons.append("INR weakening")
        
        # Previous day's Indian market sentiment
        if overview.sensex and overview.nifty:
            avg_change = (overview.sensex.change_pct + overview.nifty.change_pct) / 2
            if avg_change > 0.5:
                bullish_signals += 1
                reasons.append("Previous session closed strong")
            elif avg_change < -0.5:
                bearish_signals += 1
                reasons.append("Previous session closed weak")
        
        # Determine outlook
        if bullish_signals >= bearish_signals + 3:
            outlook = "STRONGLY BULLISH"
        elif bullish_signals > bearish_signals:
            outlook = "BULLISH"
        elif bearish_signals >= bullish_signals + 3:
            outlook = "STRONGLY BEARISH"
        elif bearish_signals > bullish_signals:
            outlook = "BEARISH"
        else:
            outlook = "NEUTRAL"
        
        # Create reason string
        reason = "; ".join(reasons[:3]) if reasons else "Mixed global cues"
        
        return outlook, reason
