"""
Recovery Stock Screener.
Finds stocks that have fallen significantly but are showing recovery.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd

from app.data.models import RecoveryCandidate, Trend
from app.data.nse_client import NSEClient
from app.analysis.technical import TechnicalAnalyzer

logger = logging.getLogger(__name__)


class RecoveryScreener:
    """Screen for recovery candidates."""
    
    def __init__(
        self,
        min_decline_pct: float = 20.0,
        max_decline_pct: float = 50.0,
        reference_date: Optional[str] = None,  # Format: "YYYY-MM-DD"
    ):
        """
        Initialize the recovery screener.
        
        Args:
            min_decline_pct: Minimum decline percentage to qualify
            max_decline_pct: Maximum decline (avoid value traps)
            reference_date: Reference date for measuring decline (default: 90 days ago)
        """
        self._min_decline = min_decline_pct
        self._max_decline = max_decline_pct
        self._reference_date = reference_date
        
        self._nse_client = NSEClient()
        self._technical = TechnicalAnalyzer()
    
    def screen(self, stocks: list = None) -> list[RecoveryCandidate]:
        """
        Screen for recovery candidates.
        
        Args:
            stocks: List of StockSnapshot to screen (optional, fetches all if not provided)
            
        Returns:
            list: Recovery candidates sorted by recovery potential
        """
        if stocks is None:
            stocks = self._nse_client.fetch_all_stocks(include_micro=True)
        
        logger.info(f"Screening {len(stocks)} stocks for recovery candidates...")
        
        candidates = []
        
        for stock in stocks:
            candidate = self._analyze_recovery(stock)
            if candidate and candidate.is_recovering:
                candidates.append(candidate)
        
        # Sort by recovery potential (highest recovery from low with uptrend)
        candidates.sort(
            key=lambda x: (
                x.trend in [Trend.UPTREND, Trend.STRONG_UPTREND],
                x.recovery_from_low_pct,
            ),
            reverse=True,
        )
        
        logger.info(f"Found {len(candidates)} recovery candidates")
        return candidates
    
    def _analyze_recovery(self, stock) -> Optional[RecoveryCandidate]:
        """Analyze a single stock for recovery potential."""
        try:
            # Fetch 6 months of history
            df = self._nse_client.fetch_stock_history(stock.symbol, period="6mo")
            
            if df is None or df.empty or len(df) < 20:
                return None
            
            close = df["Close"]
            current_price = float(close.iloc[-1])
            
            # Calculate reference price
            if self._reference_date:
                ref_date = pd.to_datetime(self._reference_date)
            else:
                ref_date = datetime.now() - timedelta(days=90)
            
            # Get closest price to reference date
            df_indexed = df.copy()
            df_indexed.index = pd.to_datetime(df_indexed.index)
            
            mask = df_indexed.index <= ref_date
            if mask.any():
                reference_price = float(df_indexed.loc[mask, "Close"].iloc[-1])
            else:
                reference_price = float(close.iloc[0])
            
            # Peak and low prices
            peak_price = float(close.max())
            low_price = float(close.min())
            
            # Calculate metrics
            decline_from_ref = ((current_price - reference_price) / reference_price) * 100
            decline_from_peak = ((current_price - peak_price) / peak_price) * 100
            recovery_from_low = ((current_price - low_price) / low_price) * 100 if low_price > 0 else 0
            
            # Recent change (last 5 days)
            if len(df) >= 5:
                recent_change = ((current_price - float(close.iloc[-5])) / float(close.iloc[-5])) * 100
            else:
                recent_change = 0
            
            # Technical analysis for trend
            indicators = self._technical.analyze(df)
            
            # Check if stock qualifies
            significant_decline = (
                decline_from_ref <= -self._min_decline 
                or decline_from_peak <= -self._min_decline
            )
            
            not_value_trap = decline_from_peak > -self._max_decline
            
            is_recovering = (
                significant_decline
                and not_value_trap
                and indicators.trend in [Trend.UPTREND, Trend.STRONG_UPTREND, Trend.SIDEWAYS]
                and recovery_from_low > 5  # At least 5% recovery from low
            )
            
            # Generate reasons
            reasons = []
            if decline_from_peak <= -self._min_decline:
                reasons.append(f"Down {abs(decline_from_peak):.1f}% from 52-week high")
            if recovery_from_low > 10:
                reasons.append(f"Already recovered {recovery_from_low:.1f}% from low")
            if indicators.trend in [Trend.UPTREND, Trend.STRONG_UPTREND]:
                reasons.append("Currently in uptrend")
            if indicators.rsi and indicators.rsi < 40:
                reasons.append(f"RSI at {indicators.rsi:.0f} suggests oversold")
            if recent_change > 0:
                reasons.append(f"Up {recent_change:.1f}% in last 5 days")
            
            return RecoveryCandidate(
                symbol=stock.symbol,
                company_name=stock.company_name,
                sector=stock.sector,
                current_price=current_price,
                reference_price=reference_price,
                peak_price=peak_price,
                low_price=low_price,
                decline_from_ref_pct=round(decline_from_ref, 2),
                decline_from_peak_pct=round(decline_from_peak, 2),
                recovery_from_low_pct=round(recovery_from_low, 2),
                recent_change_pct=round(recent_change, 2),
                trend=indicators.trend,
                rsi=indicators.rsi,
                is_recovering=is_recovering,
                reasons=reasons[:3],
            )
            
        except Exception as e:
            logger.debug(f"Failed to analyze {stock.symbol}: {e}")
            return None
