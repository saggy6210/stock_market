"""
Technical Analysis Module.
Calculates technical indicators for stock analysis.
"""

import logging
from typing import Optional
import numpy as np
import pandas as pd

from app.data.models import TechnicalIndicators, Trend

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    """Calculate technical indicators for stocks."""
    
    def __init__(self):
        """Initialize the technical analyzer."""
        pass
    
    def analyze(self, df: pd.DataFrame) -> TechnicalIndicators:
        """
        Calculate all technical indicators for a stock.
        
        Args:
            df: DataFrame with OHLCV data (columns: Open, High, Low, Close, Volume)
            
        Returns:
            TechnicalIndicators: Calculated indicators
        """
        if df is None or df.empty or len(df) < 20:
            return TechnicalIndicators()
        
        indicators = TechnicalIndicators()
        
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df.get("Volume", pd.Series([0] * len(df)))
        
        # Moving Averages
        indicators.sma_20 = self._sma(close, 20)
        indicators.sma_50 = self._sma(close, 50) if len(df) >= 50 else None
        indicators.sma_200 = self._sma(close, 200) if len(df) >= 200 else None
        indicators.ema_12 = self._ema(close, 12)
        indicators.ema_26 = self._ema(close, 26)
        
        # RSI
        indicators.rsi = self._rsi(close, 14)
        
        # MACD
        macd_result = self._macd(close)
        if macd_result:
            indicators.macd = macd_result["macd"]
            indicators.macd_signal = macd_result["signal"]
            indicators.macd_histogram = macd_result["histogram"]
        
        # ADX
        indicators.adx = self._adx(high, low, close, 14)
        
        # Trend
        indicators.trend = self._determine_trend(df, indicators)
        
        # Support/Resistance
        support, resistance = self._support_resistance(df)
        indicators.support = support
        indicators.resistance = resistance
        
        # ATR
        indicators.atr = self._atr(high, low, close, 14)
        
        # Bollinger Bands
        bb = self._bollinger_bands(close, 20)
        if bb:
            indicators.bollinger_upper = bb["upper"]
            indicators.bollinger_lower = bb["lower"]
        
        return indicators
    
    def _sma(self, series: pd.Series, period: int) -> Optional[float]:
        """Calculate Simple Moving Average."""
        if len(series) < period:
            return None
        return float(series.tail(period).mean())
    
    def _ema(self, series: pd.Series, period: int) -> Optional[float]:
        """Calculate Exponential Moving Average."""
        if len(series) < period:
            return None
        ema = series.ewm(span=period, adjust=False).mean()
        return float(ema.iloc[-1])
    
    def _rsi(self, series: pd.Series, period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index."""
        if len(series) < period + 1:
            return None
        
        delta = series.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss.replace(0, np.inf)
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else None
    
    def _macd(
        self,
        series: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> Optional[dict]:
        """Calculate MACD indicator."""
        if len(series) < slow + signal:
            return None
        
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return {
            "macd": float(macd_line.iloc[-1]),
            "signal": float(signal_line.iloc[-1]),
            "histogram": float(histogram.iloc[-1]),
        }
    
    def _adx(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14,
    ) -> Optional[float]:
        """Calculate Average Directional Index."""
        if len(close) < period * 2:
            return None
        
        try:
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean()
            
            plus_dm = high.diff()
            minus_dm = -low.diff()
            plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
            minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
            
            plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
            minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
            
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.rolling(period).mean()
            
            return float(adx.iloc[-1]) if not np.isnan(adx.iloc[-1]) else None
        except Exception:
            return None
    
    def _atr(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14,
    ) -> Optional[float]:
        """Calculate Average True Range."""
        if len(close) < period + 1:
            return None
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return float(atr.iloc[-1]) if not np.isnan(atr.iloc[-1]) else None
    
    def _bollinger_bands(
        self,
        series: pd.Series,
        period: int = 20,
        std_dev: float = 2.0,
    ) -> Optional[dict]:
        """Calculate Bollinger Bands."""
        if len(series) < period:
            return None
        
        sma = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        
        return {
            "upper": float(upper.iloc[-1]),
            "middle": float(sma.iloc[-1]),
            "lower": float(lower.iloc[-1]),
        }
    
    def _support_resistance(
        self,
        df: pd.DataFrame,
        window: int = 20,
    ) -> tuple[Optional[float], Optional[float]]:
        """Calculate support and resistance levels."""
        if len(df) < window:
            return None, None
        
        recent = df.tail(window)
        support = float(recent["Low"].min())
        resistance = float(recent["High"].max())
        
        return support, resistance
    
    def _determine_trend(
        self,
        df: pd.DataFrame,
        indicators: TechnicalIndicators,
    ) -> Trend:
        """Determine the current trend."""
        if len(df) < 20:
            return Trend.SIDEWAYS
        
        close = df["Close"].iloc[-1]
        
        # Check SMA alignment
        sma_bullish = 0
        sma_bearish = 0
        
        if indicators.sma_20 and close > indicators.sma_20:
            sma_bullish += 1
        elif indicators.sma_20:
            sma_bearish += 1
        
        if indicators.sma_50 and close > indicators.sma_50:
            sma_bullish += 1
        elif indicators.sma_50:
            sma_bearish += 1
        
        if indicators.sma_200 and close > indicators.sma_200:
            sma_bullish += 1
        elif indicators.sma_200:
            sma_bearish += 1
        
        # Check MACD
        macd_bullish = (
            indicators.macd_histogram is not None 
            and indicators.macd_histogram > 0
        )
        
        # Check ADX for trend strength
        strong_trend = indicators.adx is not None and indicators.adx > 25
        
        # Determine trend
        if sma_bullish >= 2 and macd_bullish:
            return Trend.STRONG_UPTREND if strong_trend else Trend.UPTREND
        elif sma_bearish >= 2 and not macd_bullish:
            return Trend.STRONG_DOWNTREND if strong_trend else Trend.DOWNTREND
        else:
            return Trend.SIDEWAYS
