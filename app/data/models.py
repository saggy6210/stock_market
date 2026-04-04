"""
Pydantic Data Models.
Defines the core data structures used throughout the application.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class Signal(Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class Trend(Enum):
    STRONG_UPTREND = "STRONG_UPTREND"
    UPTREND = "UPTREND"
    SIDEWAYS = "SIDEWAYS"
    DOWNTREND = "DOWNTREND"
    STRONG_DOWNTREND = "STRONG_DOWNTREND"


class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class StockSnapshot:
    """Represents a stock's current market snapshot."""
    symbol: str = ""
    company_name: str = ""
    sector: str = ""
    segment: str = ""  # Large/Mid/Small/Micro cap
    price: float = 0.0
    open_price: float = 0.0
    high: float = 0.0
    low: float = 0.0
    prev_close: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    volume: int = 0
    fifty_two_week_high: float = 0.0
    fifty_two_week_low: float = 0.0
    pe_ratio: Optional[float] = None
    market_cap: Optional[float] = None


@dataclass
class TechnicalIndicators:
    """Technical analysis indicators for a stock."""
    # Moving Averages
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    
    # Momentum
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    
    # Trend
    adx: Optional[float] = None
    trend: Optional[Trend] = None
    
    # Support/Resistance
    support: Optional[float] = None
    resistance: Optional[float] = None
    
    # Volatility
    atr: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None


@dataclass
class StockRecommendation:
    """Stock recommendation with analysis."""
    symbol: str
    company_name: str
    sector: str = ""
    segment: str = ""
    
    # Prices
    current_price: float = 0.0
    target_price: float = 0.0
    stop_loss: float = 0.0
    expected_return: float = 0.0
    
    # Scores (0-100)
    overall_score: float = 0.0
    technical_score: float = 0.0
    trend_score: float = 0.0
    momentum_score: float = 0.0
    volume_score: float = 0.0
    
    # Signals
    signal: Signal = Signal.HOLD
    risk_level: RiskLevel = RiskLevel.MEDIUM
    confidence: float = 0.0
    
    # Indicators
    rsi: Optional[float] = None
    trend: Optional[Trend] = None
    macd_signal: str = ""
    
    # Reasons
    reasons: list[str] = field(default_factory=list)


@dataclass
class RecoveryCandidate:
    """Stock showing recovery potential."""
    symbol: str
    company_name: str
    sector: str = ""
    
    current_price: float = 0.0
    reference_price: float = 0.0  # Price on reference date
    peak_price: float = 0.0
    low_price: float = 0.0
    
    decline_from_ref_pct: float = 0.0
    decline_from_peak_pct: float = 0.0
    recovery_from_low_pct: float = 0.0
    recent_change_pct: float = 0.0  # Last 5 days
    
    trend: Optional[Trend] = None
    rsi: Optional[float] = None
    
    is_recovering: bool = False
    reasons: list[str] = field(default_factory=list)


@dataclass
class PortfolioHolding:
    """Single holding in portfolio."""
    symbol: str
    quantity: int = 0
    avg_cost: float = 0.0
    current_price: float = 0.0
    investment: float = 0.0
    current_value: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    recommendation: Optional[StockRecommendation] = None


@dataclass
class DailyReport:
    """Daily market analysis report."""
    date: str
    market_status: str = ""
    
    # Top picks
    buy_signals: list[StockRecommendation] = field(default_factory=list)
    sell_signals: list[StockRecommendation] = field(default_factory=list)
    
    # Recovery stocks
    recovery_candidates: list[RecoveryCandidate] = field(default_factory=list)
    
    # Portfolio (if provided)
    portfolio_analysis: list[PortfolioHolding] = field(default_factory=list)
    
    # Summary
    total_stocks_analyzed: int = 0
    strong_buys: int = 0
    strong_sells: int = 0
