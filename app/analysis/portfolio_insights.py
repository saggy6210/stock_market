"""
Portfolio Insights Module.
Generates comprehensive portfolio analysis with actionable recommendations.

Features:
- Portfolio summary (value, P/L, allocation, sector exposure, risk flags)
- Stock movement predictions for portfolio holdings
- Relevant news for portfolio stocks
- Buy/Hold/Sell signals for each stock (long-term focus)
- Fundamental strength analysis for dip-buying opportunities
- Weak stock identification for exit strategies
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf

from app.data.nse_client import NSEClient
from app.analysis.technical import TechnicalAnalyzer
from app.analysis.recommendation import RecommendationEngine
from app.analysis.market_intelligence import MarketIntelligenceService, FundamentalData
from app.analysis.news_aggregator import NewsAggregator, NewsItem

logger = logging.getLogger(__name__)

# Timeout for yfinance API calls per stock (seconds)
YFINANCE_TIMEOUT = 5


class PortfolioSignal(Enum):
    """Portfolio-specific signals for long-term investing."""
    AGGRESSIVE_BUY = "AGGRESSIVE BUY"  # Strong fundamentals, average aggressively on dips
    BUY_ON_DIP = "BUY ON DIP"          # Good stock, buy more if it falls
    HOLD = "HOLD"                       # Hold current position
    REDUCE = "REDUCE"                   # Consider partial exit during recovery
    EXIT = "EXIT"                       # Weak fundamentals, exit during recovery


class RiskLevel(Enum):
    """Risk classification for holdings."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    VERY_HIGH = "Very High"


@dataclass
class HoldingAnalysis:
    """Comprehensive analysis for a single holding."""
    symbol: str
    company_name: str = ""
    sector: str = ""
    
    # Position details
    quantity: int = 0
    avg_cost: float = 0.0
    current_price: float = 0.0
    
    # Value metrics
    investment: float = 0.0
    current_value: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    day_change_pct: float = 0.0
    
    # Allocation
    portfolio_weight: float = 0.0  # % of total portfolio
    
    # Technical analysis
    rsi: Optional[float] = None
    trend: str = "Unknown"  # Uptrend/Downtrend/Sideways
    support: Optional[float] = None
    resistance: Optional[float] = None
    
    # Fundamental analysis
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    roe: Optional[float] = None
    debt_to_equity: Optional[float] = None
    revenue_growth: Optional[float] = None
    fundamental_score: float = 0.0  # 0-100
    
    # FII/DII activity
    fii_holding_pct: Optional[float] = None
    fii_change: Optional[float] = None  # QoQ change
    dii_holding_pct: Optional[float] = None
    
    # Recommendation
    signal: PortfolioSignal = PortfolioSignal.HOLD
    confidence: float = 0.0
    risk_level: RiskLevel = RiskLevel.MEDIUM
    
    # Key reasons
    reasons: list[str] = field(default_factory=list)
    
    # Predicted movement
    predicted_direction: str = ""  # UP/DOWN
    predicted_confidence: float = 0.0
    prediction_reason: str = ""
    
    # Target prices
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    
    # Price decline tracking from key dates
    decline_from_feb28: Optional[float] = None  # % decline since Feb 28, 2026
    decline_from_jan1: Optional[float] = None   # % decline since Jan 1, 2026
    decline_from_1yr: Optional[float] = None    # % decline since 1 year ago
    decline_from_2yr: Optional[float] = None    # % decline since 2+ years ago
    
    # Prices at key dates
    price_feb28: Optional[float] = None
    price_jan1: Optional[float] = None
    price_1yr_ago: Optional[float] = None


@dataclass
class StockDeclineCategory:
    """Stocks categorized by decline percentage."""
    down_20_30: list[str] = field(default_factory=list)  # 20-30% decline
    down_30_40: list[str] = field(default_factory=list)  # 30-40% decline
    down_40_plus: list[str] = field(default_factory=list)  # 40%+ decline


@dataclass
class DeclineSummary:
    """Summary of stock declines from key dates."""
    since_feb28_2026: StockDeclineCategory = field(default_factory=StockDeclineCategory)
    since_jan1_2026: StockDeclineCategory = field(default_factory=StockDeclineCategory)
    since_last_year: StockDeclineCategory = field(default_factory=StockDeclineCategory)
    since_2_years: StockDeclineCategory = field(default_factory=StockDeclineCategory)


@dataclass
class DetailedBuyRecommendation:
    """Detailed strong buy recommendation with quantity and reasons."""
    symbol: str
    company_name: str = ""
    sector: str = ""
    
    # Current position
    current_price: float = 0.0
    current_holding_qty: int = 0
    current_avg_cost: float = 0.0
    
    # Recommendation
    signal: str = "STRONG BUY"
    recommended_qty: int = 0  # Additional quantity to buy
    recommended_investment: float = 0.0  # Amount in ₹
    
    # Price targets
    entry_price_range: str = ""
    target_price: float = 0.0
    stop_loss: float = 0.0
    expected_return_pct: float = 0.0
    
    # Decline metrics
    decline_from_high: float = 0.0
    decline_from_feb28: float = 0.0
    decline_from_jan1: float = 0.0
    
    # Scoring
    fundamental_score: float = 0.0
    technical_score: float = 0.0
    overall_confidence: float = 0.0
    
    # Detailed reasons (categorized)
    fii_dii_activity: str = ""
    government_policy: str = ""
    earnings_profit: str = ""
    order_booking: str = ""
    news_catalyst: str = ""
    technical_reason: str = ""
    
    # All reasons combined
    reasons: list[str] = field(default_factory=list)
    
    # Related news
    related_news: list[str] = field(default_factory=list)


@dataclass
class SectorAllocation:
    """Sector allocation details."""
    sector: str
    value: float
    weight_pct: float
    pnl: float
    pnl_pct: float
    stock_count: int


@dataclass
class PortfolioRiskFlags:
    """Risk flags for portfolio."""
    concentration_risk: bool = False  # Top 5 holdings > 50%
    sector_concentration: bool = False  # Single sector > 40%
    high_loss_stocks: int = 0  # Stocks with > 30% loss
    high_beta_exposure: float = 0.0
    debt_risk_stocks: list[str] = field(default_factory=list)
    news_risk_stocks: list[str] = field(default_factory=list)  # Stocks with negative news
    
    def get_flags(self) -> list[str]:
        """Get list of active risk flags."""
        flags = []
        if self.concentration_risk:
            flags.append("⚠️ High concentration risk (top 5 holdings > 50%)")
        if self.sector_concentration:
            flags.append("⚠️ Sector concentration risk (single sector > 40%)")
        if self.high_loss_stocks > 3:
            flags.append(f"⚠️ {self.high_loss_stocks} stocks with >30% loss")
        if self.debt_risk_stocks:
            flags.append(f"⚠️ High debt: {', '.join(self.debt_risk_stocks[:3])}")
        if self.news_risk_stocks:
            flags.append(f"⚠️ Negative news: {', '.join(self.news_risk_stocks[:3])}")
        return flags


@dataclass
class PortfolioSummary:
    """Portfolio summary with key metrics."""
    total_investment: float = 0.0
    current_value: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    day_change: float = 0.0
    day_change_pct: float = 0.0
    
    # Stock counts
    total_stocks: int = 0
    profitable_stocks: int = 0
    loss_making_stocks: int = 0
    
    # Top performers
    top_gainers: list[str] = field(default_factory=list)
    top_losers: list[str] = field(default_factory=list)
    
    # Sector allocation
    sector_allocation: list[SectorAllocation] = field(default_factory=list)
    
    # Risk assessment
    risk_flags: PortfolioRiskFlags = field(default_factory=PortfolioRiskFlags)
    overall_risk_level: RiskLevel = RiskLevel.MEDIUM


@dataclass
class NewInvestmentSuggestion:
    """Suggested new investment opportunity."""
    symbol: str
    company_name: str
    sector: str
    current_price: float
    
    # Why buy
    reasons: list[str] = field(default_factory=list)
    
    # Target
    entry_range: str = ""
    target_price: float = 0.0
    stop_loss: float = 0.0
    
    # Scores
    fundamental_score: float = 0.0
    technical_score: float = 0.0
    confidence: float = 0.0


@dataclass
class PortfolioInsights:
    """Complete portfolio insights."""
    date: str
    
    # Summary
    summary: PortfolioSummary
    
    # All holdings with analysis
    holdings: list[HoldingAnalysis] = field(default_factory=list)
    
    # Categorized signals
    aggressive_buy_stocks: list[HoldingAnalysis] = field(default_factory=list)
    buy_on_dip_stocks: list[HoldingAnalysis] = field(default_factory=list)
    hold_stocks: list[HoldingAnalysis] = field(default_factory=list)
    reduce_stocks: list[HoldingAnalysis] = field(default_factory=list)
    exit_stocks: list[HoldingAnalysis] = field(default_factory=list)
    
    # Movement predictions (top 20)
    predictions: list[HoldingAnalysis] = field(default_factory=list)
    
    # Relevant news
    portfolio_news: list[NewsItem] = field(default_factory=list)
    
    # New investment suggestions
    new_suggestions: list[NewInvestmentSuggestion] = field(default_factory=list)
    
    # Decline summary from key dates
    decline_summary: DeclineSummary = field(default_factory=DeclineSummary)
    
    # Top 10 detailed strong buy recommendations
    detailed_buy_recommendations: list[DetailedBuyRecommendation] = field(default_factory=list)
    
    # Strategy context
    market_outlook: str = ""
    strategy_notes: str = ""


class PortfolioInsightsGenerator:
    """
    Generate comprehensive portfolio insights.
    
    Analyzes portfolio holdings for:
    - Fundamental strength
    - Technical position
    - FII/DII activity
    - News sentiment
    - Buy/Hold/Sell recommendations
    """
    
    def __init__(self, holdings_path: str = None):
        """Initialize the portfolio insights generator."""
        self._holdings_path = holdings_path or "/home/sachavan/github/stock_market/holdings.csv"
        self._nse_client = NSEClient()
        self._technical = TechnicalAnalyzer()
        self._recommendation = RecommendationEngine()
        self._market_intel = MarketIntelligenceService()
        self._news_aggregator = NewsAggregator()
    
    def generate(self) -> PortfolioInsights:
        """
        Generate comprehensive portfolio insights.
        
        Returns:
            PortfolioInsights: Complete analysis
        """
        logger.info(f"Generating portfolio insights from {self._holdings_path}...")
        
        # Read holdings
        holdings_df = self._read_holdings()
        if holdings_df.empty:
            logger.error("No holdings found")
            return PortfolioInsights(
                date=datetime.now().strftime("%Y-%m-%d"),
                summary=PortfolioSummary(),
            )
        
        # Analyze each holding
        holdings = self._analyze_holdings(holdings_df)
        
        # Calculate portfolio summary
        summary = self._calculate_summary(holdings)
        
        # Categorize by signal
        aggressive_buy = [h for h in holdings if h.signal == PortfolioSignal.AGGRESSIVE_BUY]
        buy_on_dip = [h for h in holdings if h.signal == PortfolioSignal.BUY_ON_DIP]
        hold = [h for h in holdings if h.signal == PortfolioSignal.HOLD]
        reduce = [h for h in holdings if h.signal == PortfolioSignal.REDUCE]
        exit_stocks = [h for h in holdings if h.signal == PortfolioSignal.EXIT]
        
        # Sort by confidence
        aggressive_buy.sort(key=lambda x: x.confidence, reverse=True)
        buy_on_dip.sort(key=lambda x: x.confidence, reverse=True)
        exit_stocks.sort(key=lambda x: x.fundamental_score)  # Weakest first
        
        # Get predictions (top 20 based on prediction confidence)
        predictions = sorted(
            [h for h in holdings if h.predicted_direction],
            key=lambda x: x.predicted_confidence,
            reverse=True
        )[:20]
        
        # Get relevant news
        symbols = [h.symbol for h in holdings]
        portfolio_news = self._get_portfolio_news(symbols)
        
        # Generate strategy notes
        strategy_notes = self._generate_strategy_notes(summary, holdings)
        
        # Calculate decline summary from key dates
        decline_summary = self._calculate_decline_summary(holdings)
        
        # Generate top 10 detailed buy recommendations
        detailed_recommendations = self._generate_detailed_buy_recommendations(
            holdings, portfolio_news
        )
        
        # Create insights
        insights = PortfolioInsights(
            date=datetime.now().strftime("%Y-%m-%d"),
            summary=summary,
            holdings=holdings,
            aggressive_buy_stocks=aggressive_buy,
            buy_on_dip_stocks=buy_on_dip,
            hold_stocks=hold,
            reduce_stocks=reduce,
            exit_stocks=exit_stocks,
            predictions=predictions,
            portfolio_news=portfolio_news,
            decline_summary=decline_summary,
            detailed_buy_recommendations=detailed_recommendations,
            market_outlook=self._get_market_outlook(),
            strategy_notes=strategy_notes,
        )
        
        logger.info(
            f"Portfolio insights generated: {len(holdings)} stocks, "
            f"P/L: {summary.total_pnl_pct:.2f}%, "
            f"Aggressive Buy: {len(aggressive_buy)}, Exit: {len(exit_stocks)}"
        )
        
        return insights
    
    def _read_holdings(self) -> pd.DataFrame:
        """Read holdings from CSV."""
        try:
            df = pd.read_csv(self._holdings_path)
            
            # Normalize column names
            df.columns = df.columns.str.strip().str.replace(".", "", regex=False)
            
            return df
        except Exception as e:
            logger.error(f"Failed to read holdings: {e}")
            return pd.DataFrame()
    
    def _analyze_holdings(self, df: pd.DataFrame) -> list[HoldingAnalysis]:
        """Analyze all holdings with parallel enrichment."""
        holdings = []
        total_value = df["Cur val"].sum() if "Cur val" in df.columns else 0
        
        # First pass: Create basic holdings from CSV data
        basic_holdings = []
        for _, row in df.iterrows():
            try:
                holding = self._create_basic_holding(row, total_value)
                if holding:
                    basic_holdings.append(holding)
            except Exception as e:
                logger.debug(f"Error creating holding {row.get('Instrument')}: {e}")
                continue
        
        logger.info(f"Created {len(basic_holdings)} basic holdings, enriching with fundamentals...")
        
        # Second pass: Enrich holdings in parallel with timeout
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(self._enrich_holding_with_timeout, h): h 
                for h in basic_holdings
            }
            
            for future in as_completed(futures, timeout=60):  # Overall timeout
                holding = futures[future]
                try:
                    future.result(timeout=YFINANCE_TIMEOUT)
                except Exception as e:
                    logger.debug(f"Enrichment failed for {holding.symbol}: {e}")
        
        # Third pass: Calculate scores and signals for all holdings
        for holding in basic_holdings:
            holding.fundamental_score = self._calculate_fundamental_score(holding)
            self._generate_signal(holding)
            self._generate_prediction(holding)
            holdings.append(holding)
        
        logger.info(f"Analyzed {len(holdings)} holdings successfully")
        return holdings
    
    def _create_basic_holding(self, row: pd.Series, total_value: float) -> Optional[HoldingAnalysis]:
        """Create a basic holding from CSV row data."""
        symbol = str(row.get("Instrument", "")).strip()
        if not symbol:
            return None
        
        holding = HoldingAnalysis(symbol=symbol)
        
        # Basic position data from CSV
        holding.quantity = int(row.get("Qty", 0))
        holding.avg_cost = float(row.get("Avg cost", 0))
        holding.current_price = float(row.get("LTP", 0))
        holding.investment = float(row.get("Invested", 0))
        holding.current_value = float(row.get("Cur val", 0))
        holding.pnl = float(row.get("P&L", 0))
        
        # Calculate P&L percentage
        if holding.investment > 0:
            holding.pnl_pct = (holding.pnl / holding.investment) * 100
        
        # Day change
        holding.day_change_pct = float(row.get("Day chg", 0))
        
        # Portfolio weight
        if total_value > 0:
            holding.portfolio_weight = (holding.current_value / total_value) * 100
        
        # Set default company name
        holding.company_name = symbol
        holding.sector = "Unknown"
        
        return holding
    
    def _enrich_holding_with_timeout(self, holding: HoldingAnalysis) -> None:
        """Enrich holding with timeout protection."""
        try:
            self._enrich_holding_data(holding)
        except Exception as e:
            logger.debug(f"Enrichment timeout/error for {holding.symbol}: {e}")
    
    def _enrich_holding_data(self, holding: HoldingAnalysis) -> None:
        """Enrich holding with additional data from various sources (fast mode)."""
        try:
            # Try Yahoo Finance - only get basic info, skip historical data for speed
            for suffix in [".NS", ".BO"]:
                try:
                    ticker = yf.Ticker(f"{holding.symbol}{suffix}")
                    info = ticker.fast_info  # Use fast_info instead of info
                    
                    if info and hasattr(info, 'last_price') and info.last_price:
                        # Get full info only if fast_info works
                        full_info = ticker.info
                        holding.company_name = full_info.get("shortName", holding.symbol)
                        holding.sector = full_info.get("sector", "Unknown")
                        holding.pe_ratio = full_info.get("trailingPE")
                        holding.pb_ratio = full_info.get("priceToBook")
                        holding.roe = full_info.get("returnOnEquity", 0) * 100 if full_info.get("returnOnEquity") else None
                        holding.debt_to_equity = full_info.get("debtToEquity")
                        holding.revenue_growth = full_info.get("revenueGrowth", 0) * 100 if full_info.get("revenueGrowth") else None
                        break
                except Exception:
                    continue
                    
        except Exception as e:
            logger.debug(f"Error enriching {holding.symbol}: {e}")
    
    def _calculate_technicals(self, holding: HoldingAnalysis, hist: pd.DataFrame) -> None:
        """Calculate technical indicators."""
        try:
            close = hist["Close"]
            
            # RSI
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            holding.rsi = float(100 - (100 / (1 + rs.iloc[-1]))) if not pd.isna(rs.iloc[-1]) else None
            
            # Trend (using 50-day SMA)
            sma50 = close.rolling(50).mean()
            sma20 = close.rolling(20).mean()
            
            if len(sma50) > 0 and not pd.isna(sma50.iloc[-1]):
                current = close.iloc[-1]
                if current > sma50.iloc[-1] and sma20.iloc[-1] > sma50.iloc[-1]:
                    holding.trend = "Uptrend"
                elif current < sma50.iloc[-1] and sma20.iloc[-1] < sma50.iloc[-1]:
                    holding.trend = "Downtrend"
                else:
                    holding.trend = "Sideways"
            
            # Support and Resistance (simple method using recent lows/highs)
            recent = hist.tail(20)
            holding.support = float(recent["Low"].min())
            holding.resistance = float(recent["High"].max())
            
            # Target price (simple projection)
            if holding.trend == "Uptrend":
                holding.target_price = holding.current_price * 1.15
            else:
                holding.target_price = holding.resistance
            
            # Stop loss
            holding.stop_loss = holding.support * 0.95
            
        except Exception as e:
            logger.debug(f"Error calculating technicals for {holding.symbol}: {e}")
    
    def _calculate_fundamental_score(self, holding: HoldingAnalysis) -> float:
        """
        Calculate fundamental score (0-100).
        
        When fundamental data is available:
        - ROE > 15% (+25)
        - Debt/Equity < 1 (+20)
        - Revenue Growth > 10% (+20)
        - PE ratio reasonable (+15)
        - FII increasing (+10)
        
        When no fundamental data:
        - Use portfolio weight and sector assumptions
        """
        has_fundamental_data = any([
            holding.roe is not None,
            holding.debt_to_equity is not None,
            holding.pe_ratio is not None,
            holding.revenue_growth is not None
        ])
        
        if has_fundamental_data:
            score = 50  # Base score when we have data
            
            # ROE
            if holding.roe:
                if holding.roe > 20:
                    score += 25
                elif holding.roe > 15:
                    score += 15
                elif holding.roe > 10:
                    score += 5
                elif holding.roe < 5:
                    score -= 15
            
            # Debt to Equity
            if holding.debt_to_equity is not None:
                if holding.debt_to_equity < 0.5:
                    score += 20
                elif holding.debt_to_equity < 1:
                    score += 10
                elif holding.debt_to_equity > 2:
                    score -= 20
            
            # Revenue Growth
            if holding.revenue_growth:
                if holding.revenue_growth > 20:
                    score += 20
                elif holding.revenue_growth > 10:
                    score += 10
                elif holding.revenue_growth < 0:
                    score -= 15
            
            # PE Ratio
            if holding.pe_ratio:
                if 10 <= holding.pe_ratio <= 25:
                    score += 15
                elif holding.pe_ratio < 10:
                    score += 5  # Could be value trap
                elif holding.pe_ratio > 50:
                    score -= 10
        else:
            # No fundamental data - use heuristics based on position
            # Start with a moderate score
            score = 55
            
            # Higher weight stocks are likely quality holdings
            if holding.portfolio_weight > 5:
                score += 10
            elif holding.portfolio_weight > 2:
                score += 5
            
            # Stocks with smaller losses might be better quality
            if holding.pnl_pct > -10:
                score += 10
            elif holding.pnl_pct > -20:
                score += 5
            elif holding.pnl_pct < -50:
                score -= 15  # Very deep loss is concerning
            
            # Positive day change is a good sign
            if holding.day_change_pct > 2:
                score += 5
            elif holding.day_change_pct < -3:
                score -= 5
                score -= 10
        
        # RSI (technical health)
        if holding.rsi:
            if 40 <= holding.rsi <= 60:
                score += 10
            elif holding.rsi < 30:
                score += 5  # Oversold, potential bounce
            elif holding.rsi > 70:
                score -= 5  # Overbought
        
        return max(0, min(100, score))
    
    def _generate_signal(self, holding: HoldingAnalysis) -> None:
        """
        Generate Buy/Hold/Sell signal for a holding.
        
        Strategy context:
        - Expecting short-term downside (10-20%)
        - Strong recovery afterward
        - Identify weak stocks to exit during recovery
        - Identify strong stocks to average on dips
        """
        score = holding.fundamental_score
        pnl_pct = holding.pnl_pct
        
        reasons = []
        
        # Check if we have real fundamental data
        has_fundamental_data = any([
            holding.roe is not None,
            holding.debt_to_equity is not None,
            holding.pe_ratio is not None
        ])
        
        # Determine signal based on fundamentals and position
        if score >= 70:
            # Strong fundamentals
            if pnl_pct < -20:
                holding.signal = PortfolioSignal.AGGRESSIVE_BUY
                reasons.append("Strong fundamentals despite price decline")
                reasons.append("Excellent opportunity to average down")
            elif pnl_pct < 0:
                holding.signal = PortfolioSignal.BUY_ON_DIP
                reasons.append("Solid fundamentals, buy on further weakness")
            else:
                holding.signal = PortfolioSignal.HOLD
                reasons.append("Strong stock, hold through volatility")
            
            if holding.roe and holding.roe > 15:
                reasons.append(f"High ROE: {holding.roe:.1f}%")
            if holding.debt_to_equity and holding.debt_to_equity < 0.5:
                reasons.append("Low debt, strong balance sheet")
                
        elif score >= 55:
            # Moderate fundamentals or unknown fundamentals
            if pnl_pct < -35:
                # Deep loss - consider averaging if decent score
                holding.signal = PortfolioSignal.BUY_ON_DIP
                reasons.append("Significant decline, consider averaging")
                if not has_fundamental_data:
                    reasons.append("Verify fundamentals before buying")
            elif pnl_pct < -20:
                holding.signal = PortfolioSignal.HOLD
                reasons.append("Moderate fundamentals, hold and review")
            elif pnl_pct > 15:
                holding.signal = PortfolioSignal.REDUCE
                reasons.append("Consider booking partial profits")
            else:
                holding.signal = PortfolioSignal.HOLD
                reasons.append("Continue to hold, monitor performance")
                
        elif score >= 45:
            # Below average fundamentals
            if pnl_pct < -40:
                holding.signal = PortfolioSignal.REDUCE
                reasons.append("Below average fundamentals with deep loss")
                reasons.append("Consider reducing on bounce")
            elif pnl_pct < -20:
                holding.signal = PortfolioSignal.HOLD
                reasons.append("Monitor closely, may need to exit")
            else:
                holding.signal = PortfolioSignal.HOLD
                reasons.append("Hold but watch for deterioration")
                
        else:
            # Weak fundamentals
            if pnl_pct < -50:
                holding.signal = PortfolioSignal.EXIT
                reasons.append("Weak stock with very deep loss")
                reasons.append("Exit on any bounce to recover capital")
            elif pnl_pct < -30:
                holding.signal = PortfolioSignal.REDUCE
                reasons.append("Weak fundamentals, reduce exposure")
            else:
                holding.signal = PortfolioSignal.HOLD
                reasons.append("Monitor - may need to exit on weakness")
            
            if holding.debt_to_equity and holding.debt_to_equity > 2:
                reasons.append(f"High debt risk: D/E {holding.debt_to_equity:.1f}")
        
        # Risk level
        if score >= 70 and (holding.debt_to_equity is None or holding.debt_to_equity < 1):
            holding.risk_level = RiskLevel.LOW
        elif score >= 50:
            holding.risk_level = RiskLevel.MEDIUM
        elif score >= 30:
            holding.risk_level = RiskLevel.HIGH
        else:
            holding.risk_level = RiskLevel.VERY_HIGH
        
        # Confidence
        holding.confidence = min(95, holding.fundamental_score + 10)
        holding.reasons = reasons[:5]
    
    def _generate_prediction(self, holding: HoldingAnalysis) -> None:
        """Generate short-term movement prediction based on available data."""
        # Use P&L, day change, and fundamental score for prediction
        
        if holding.rsi and holding.rsi < 30:
            holding.predicted_direction = "UP"
            holding.predicted_confidence = 65
            holding.prediction_reason = "Oversold RSI, bounce expected"
        elif holding.rsi and holding.rsi > 70:
            holding.predicted_direction = "DOWN"
            holding.predicted_confidence = 60
            holding.prediction_reason = "Overbought RSI, pullback likely"
        elif holding.pnl_pct < -40 and holding.fundamental_score >= 60:
            holding.predicted_direction = "UP"
            holding.predicted_confidence = 65
            holding.prediction_reason = "Deeply oversold, strong fundamentals - bounce expected"
        elif holding.pnl_pct < -25 and holding.fundamental_score >= 50:
            holding.predicted_direction = "UP"
            holding.predicted_confidence = 55
            holding.prediction_reason = "Oversold with decent fundamentals"
        elif holding.day_change_pct > 3:
            holding.predicted_direction = "UP"
            holding.predicted_confidence = 60
            holding.prediction_reason = "Strong momentum, continuation likely"
        elif holding.day_change_pct < -3:
            holding.predicted_direction = "DOWN"
            holding.predicted_confidence = 55
            holding.prediction_reason = "Weak momentum, further decline possible"
        elif holding.pnl_pct > 20 and holding.fundamental_score < 50:
            holding.predicted_direction = "DOWN"
            holding.predicted_confidence = 55
            holding.prediction_reason = "Overextended with weak fundamentals"
        elif holding.day_change_pct > 0 and holding.pnl_pct > 0:
            holding.predicted_direction = "UP"
            holding.predicted_confidence = 50
            holding.prediction_reason = "Positive momentum in profitable position"
        elif holding.day_change_pct < 0 and holding.pnl_pct < -20:
            holding.predicted_direction = "DOWN"
            holding.predicted_confidence = 50
            holding.prediction_reason = "Ongoing weakness"
        else:
            holding.predicted_direction = "SIDEWAYS"
            holding.predicted_confidence = 50
            holding.prediction_reason = "Consolidation expected"
    
    def _calculate_summary(self, holdings: list[HoldingAnalysis]) -> PortfolioSummary:
        """Calculate portfolio summary."""
        summary = PortfolioSummary()
        
        if not holdings:
            return summary
        
        # Basic totals
        summary.total_investment = sum(h.investment for h in holdings)
        summary.current_value = sum(h.current_value for h in holdings)
        summary.total_pnl = summary.current_value - summary.total_investment
        summary.total_pnl_pct = (summary.total_pnl / summary.total_investment * 100) if summary.total_investment > 0 else 0
        
        # Day change (weighted average)
        if summary.current_value > 0:
            summary.day_change_pct = sum(h.day_change_pct * h.current_value for h in holdings) / summary.current_value
            summary.day_change = summary.current_value * summary.day_change_pct / 100
        
        # Stock counts
        summary.total_stocks = len(holdings)
        summary.profitable_stocks = len([h for h in holdings if h.pnl > 0])
        summary.loss_making_stocks = len([h for h in holdings if h.pnl < 0])
        
        # Top performers
        sorted_by_pnl = sorted(holdings, key=lambda x: x.pnl_pct, reverse=True)
        summary.top_gainers = [f"{h.symbol} (+{h.pnl_pct:.1f}%)" for h in sorted_by_pnl[:3] if h.pnl_pct > 0]
        summary.top_losers = [f"{h.symbol} ({h.pnl_pct:.1f}%)" for h in sorted_by_pnl[-3:] if h.pnl_pct < 0]
        
        # Sector allocation
        sector_data = {}
        for h in holdings:
            sector = h.sector or "Unknown"
            if sector not in sector_data:
                sector_data[sector] = {"value": 0, "pnl": 0, "stocks": []}
            sector_data[sector]["value"] += h.current_value
            sector_data[sector]["pnl"] += h.pnl
            sector_data[sector]["stocks"].append(h.symbol)
        
        for sector, data in sector_data.items():
            investment = sum(h.investment for h in holdings if (h.sector or "Unknown") == sector)
            pnl_pct = (data["pnl"] / investment * 100) if investment > 0 else 0
            summary.sector_allocation.append(SectorAllocation(
                sector=sector,
                value=data["value"],
                weight_pct=(data["value"] / summary.current_value * 100) if summary.current_value > 0 else 0,
                pnl=data["pnl"],
                pnl_pct=pnl_pct,
                stock_count=len(data["stocks"]),
            ))
        
        summary.sector_allocation.sort(key=lambda x: x.weight_pct, reverse=True)
        
        # Risk flags
        risk_flags = PortfolioRiskFlags()
        
        # Concentration risk
        top5_value = sum(h.current_value for h in sorted(holdings, key=lambda x: x.current_value, reverse=True)[:5])
        if top5_value / summary.current_value > 0.5:
            risk_flags.concentration_risk = True
        
        # Sector concentration
        if summary.sector_allocation and summary.sector_allocation[0].weight_pct > 40:
            risk_flags.sector_concentration = True
        
        # High loss stocks
        risk_flags.high_loss_stocks = len([h for h in holdings if h.pnl_pct < -30])
        
        # Debt risk
        risk_flags.debt_risk_stocks = [h.symbol for h in holdings if h.debt_to_equity and h.debt_to_equity > 2]
        
        summary.risk_flags = risk_flags
        
        # Overall risk level
        risk_score = 0
        if risk_flags.concentration_risk:
            risk_score += 2
        if risk_flags.sector_concentration:
            risk_score += 1
        if risk_flags.high_loss_stocks > 5:
            risk_score += 2
        elif risk_flags.high_loss_stocks > 3:
            risk_score += 1
        
        if risk_score >= 4:
            summary.overall_risk_level = RiskLevel.VERY_HIGH
        elif risk_score >= 3:
            summary.overall_risk_level = RiskLevel.HIGH
        elif risk_score >= 1:
            summary.overall_risk_level = RiskLevel.MEDIUM
        else:
            summary.overall_risk_level = RiskLevel.LOW
        
        return summary
    
    def _get_portfolio_news(self, symbols: list[str]) -> list[NewsItem]:
        """Get news relevant to portfolio stocks."""
        try:
            all_news = self._news_aggregator.fetch_all_news()
            
            # Filter news mentioning portfolio stocks
            relevant = []
            symbol_set = set(s.upper() for s in symbols)
            
            # Combine all news categories
            all_items = (
                all_news.top_stories +
                all_news.earnings_news +
                all_news.order_booking_news +
                all_news.regulatory_news
            )
            
            for item in all_items:
                # Check if any portfolio stock is mentioned
                for mentioned in item.stocks_mentioned:
                    if mentioned.upper() in symbol_set:
                        relevant.append(item)
                        break
                
                # Also check headline for symbol names
                headline_upper = item.headline.upper()
                for symbol in symbol_set:
                    if symbol in headline_upper:
                        if item not in relevant:
                            relevant.append(item)
                        break
            
            return relevant[:15]  # Top 15 relevant news
            
        except Exception as e:
            logger.warning(f"Error fetching portfolio news: {e}")
            return []
    
    def _get_market_outlook(self) -> str:
        """Get market outlook for strategy context."""
        return (
            "CAUTIOUS OPTIMISM: Short-term volatility expected due to geopolitical tensions "
            "(Iran-US, NATO dynamics, US policies). Potential 10-20% downside in near term. "
            "However, strong recovery expected afterward with possibility of new highs. "
            "Strategy: Accumulate quality stocks on dips, exit weak fundamentals during recovery."
        )
    
    def _generate_strategy_notes(self, summary: PortfolioSummary, holdings: list[HoldingAnalysis]) -> str:
        """Generate strategy notes based on portfolio analysis."""
        notes = []
        
        # Portfolio health assessment
        if summary.total_pnl_pct < -15:
            notes.append(
                f"📉 Portfolio is down {abs(summary.total_pnl_pct):.1f}%. "
                "Focus on identifying weak stocks to exit and strong stocks to average."
            )
        elif summary.total_pnl_pct < 0:
            notes.append(
                f"Portfolio slightly underwater ({summary.total_pnl_pct:.1f}%). "
                "Use market corrections to improve position quality."
            )
        
        # Strong stocks to average
        strong_down = [h for h in holdings if h.fundamental_score > 70 and h.pnl_pct < -15]
        if strong_down:
            notes.append(
                f"💪 AVERAGE ON DIPS: {', '.join(h.symbol for h in strong_down[:5])} "
                "have strong fundamentals despite being down. Consider averaging."
            )
        
        # Weak stocks to exit
        weak = [h for h in holdings if h.fundamental_score < 40]
        if weak:
            notes.append(
                f"⚠️ EXIT CANDIDATES: {', '.join(h.symbol for h in weak[:5])} "
                "have weak fundamentals. Consider exiting during market recovery."
            )
        
        # High concentration warning
        if summary.risk_flags.concentration_risk:
            notes.append(
                "🎯 DIVERSIFICATION: Top 5 holdings exceed 50% of portfolio. "
                "Consider spreading risk across more quality stocks."
            )
        
        # Fresh capital deployment
        notes.append(
            "💰 FRESH CAPITAL (₹2-5L): Wait for further correction (10-15%) "
            "before deploying. Focus on large-cap quality names and beaten-down "
            "sectors like IT, Pharma, and infrastructure."
        )
        
        return " | ".join(notes)
    
    def _calculate_decline_summary(self, holdings: list[HoldingAnalysis]) -> DeclineSummary:
        """
        Calculate stock declines from key dates.
        Uses P&L percentage as proxy for decline to avoid slow API calls.
        """
        decline_summary = DeclineSummary()
        
        # Use P&L percentage as a proxy for decline since purchase
        for holding in holdings:
            try:
                # Use P&L percentage as decline indicator
                decline_pct = holding.pnl_pct  # Negative = decline
                
                # Categorize stocks by their loss percentage
                if decline_pct <= -40:
                    decline_summary.since_feb28_2026.down_40_plus.append(f"{holding.symbol} ({decline_pct:.1f}%)")
                elif decline_pct <= -30:
                    decline_summary.since_feb28_2026.down_30_40.append(f"{holding.symbol} ({decline_pct:.1f}%)")
                elif decline_pct <= -20:
                    decline_summary.since_feb28_2026.down_20_30.append(f"{holding.symbol} ({decline_pct:.1f}%)")
                    
            except Exception as e:
                logger.debug(f"Error calculating decline for {holding.symbol}: {e}")
        
        return decline_summary
    
    def _generate_detailed_buy_recommendations(
        self,
        holdings: list[HoldingAnalysis],
        news_items: list[NewsItem]
    ) -> list[DetailedBuyRecommendation]:
        """
        Generate top 10 detailed strong buy recommendations.
        
        Includes:
        - Quantity to buy
        - Detailed reasons (FII, govt policy, earnings, orders, news)
        - Related news
        """
        recommendations = []
        
        # Filter for strong buy candidates
        candidates = [
            h for h in holdings
            if h.signal in [PortfolioSignal.AGGRESSIVE_BUY, PortfolioSignal.BUY_ON_DIP]
            and h.fundamental_score >= 50
        ]
        
        # Sort by score and decline (deeper decline = better opportunity)
        candidates.sort(
            key=lambda x: (x.fundamental_score, -x.pnl_pct),
            reverse=True
        )
        
        for holding in candidates[:10]:
            rec = self._build_detailed_recommendation(holding, news_items)
            recommendations.append(rec)
        
        return recommendations
    
    def _build_detailed_recommendation(
        self,
        holding: HoldingAnalysis,
        news_items: list[NewsItem]
    ) -> DetailedBuyRecommendation:
        """Build a detailed recommendation for a single stock."""
        rec = DetailedBuyRecommendation(
            symbol=holding.symbol,
            company_name=holding.company_name,
            sector=holding.sector,
            current_price=holding.current_price,
            current_holding_qty=holding.quantity,
            current_avg_cost=holding.avg_cost,
        )
        
        # Calculate recommended quantity (based on how much to average)
        # Target: Average down to reduce avg cost by ~10-15%
        current_investment = holding.investment
        
        if holding.pnl_pct < -30:
            # Deep loss: Suggest investing 50% of current position
            rec.recommended_investment = current_investment * 0.5
            rec.signal = "AGGRESSIVE BUY"
        elif holding.pnl_pct < -20:
            # Moderate loss: Suggest investing 30% of current position
            rec.recommended_investment = current_investment * 0.3
            rec.signal = "STRONG BUY"
        else:
            # Small loss or profit: Suggest investing 20% of current position
            rec.recommended_investment = current_investment * 0.2
            rec.signal = "BUY ON DIP"
        
        # Cap at ₹50,000 per recommendation
        rec.recommended_investment = min(rec.recommended_investment, 50000)
        
        # Calculate quantity
        if holding.current_price > 0:
            rec.recommended_qty = int(rec.recommended_investment / holding.current_price)
            rec.recommended_investment = rec.recommended_qty * holding.current_price
        
        # Entry range (current price +/- 3%)
        rec.entry_price_range = f"₹{holding.current_price * 0.97:.2f} - ₹{holding.current_price * 1.03:.2f}"
        
        # Targets
        rec.target_price = holding.target_price or holding.current_price * 1.25
        rec.stop_loss = holding.stop_loss or holding.current_price * 0.90
        rec.expected_return_pct = ((rec.target_price - holding.current_price) / holding.current_price) * 100
        
        # Decline metrics
        rec.decline_from_high = holding.pnl_pct  # Using P&L as proxy for decline
        rec.decline_from_feb28 = holding.decline_from_feb28 or 0
        rec.decline_from_jan1 = holding.decline_from_jan1 or 0
        
        # Scores
        rec.fundamental_score = holding.fundamental_score
        rec.technical_score = 50  # Base score
        if holding.rsi and holding.rsi < 30:
            rec.technical_score += 30
        elif holding.rsi and holding.rsi < 40:
            rec.technical_score += 15
        if holding.trend == "Uptrend":
            rec.technical_score += 10
        
        rec.overall_confidence = (rec.fundamental_score + rec.technical_score) / 2
        
        # Generate detailed reasons
        reasons = []
        
        # FII/DII activity
        if holding.fii_change and holding.fii_change > 0:
            rec.fii_dii_activity = f"FII increased stake by {holding.fii_change:.1f}% last quarter"
            reasons.append(f"📈 FII Buying: {rec.fii_dii_activity}")
        elif holding.fii_holding_pct and holding.fii_holding_pct > 20:
            rec.fii_dii_activity = f"High FII holding: {holding.fii_holding_pct:.1f}%"
            reasons.append(f"🏦 Institutional Support: {rec.fii_dii_activity}")
        
        # Fundamental reasons
        if holding.roe and holding.roe > 15:
            rec.earnings_profit = f"Strong ROE of {holding.roe:.1f}%"
            reasons.append(f"💰 {rec.earnings_profit}")
        
        if holding.revenue_growth and holding.revenue_growth > 10:
            reasons.append(f"📊 Revenue growth: {holding.revenue_growth:.1f}%")
        
        if holding.debt_to_equity is not None and holding.debt_to_equity < 0.5:
            reasons.append(f"🛡️ Low debt (D/E: {holding.debt_to_equity:.2f})")
        
        if holding.pe_ratio and 10 <= holding.pe_ratio <= 25:
            reasons.append(f"📉 Attractive valuation (PE: {holding.pe_ratio:.1f})")
        
        # Technical reasons
        if holding.rsi and holding.rsi < 35:
            rec.technical_reason = f"Oversold (RSI: {holding.rsi:.0f})"
            reasons.append(f"📉 {rec.technical_reason}")
        
        if holding.trend == "Uptrend":
            reasons.append("📈 Technical uptrend intact")
        
        # Decline-based reasons
        if holding.pnl_pct < -30:
            reasons.append(f"💎 Down {abs(holding.pnl_pct):.1f}% from cost - deep value opportunity")
        
        if holding.decline_from_feb28 and holding.decline_from_feb28 < -20:
            reasons.append(f"📅 Down {abs(holding.decline_from_feb28):.1f}% since Feb 28 - recovery expected")
        
        # Default reasons if none found
        if not reasons:
            reasons = [
                "Strong sector positioning",
                "Quality management track record",
                "Market leader in segment"
            ]
        
        rec.reasons = reasons[:6]  # Top 6 reasons
        
        # Related news
        symbol_upper = holding.symbol.upper()
        for news in news_items[:10]:
            if symbol_upper in news.headline.upper() or symbol_upper in [s.upper() for s in news.stocks_mentioned]:
                rec.related_news.append(news.headline[:80])
                if len(rec.related_news) >= 3:
                    break
        
        # Add sector/policy-related catalyst
        if holding.sector:
            sector_lower = holding.sector.lower()
            if "tech" in sector_lower or "it" in sector_lower:
                rec.government_policy = "Digital India push, IT export benefits"
                reasons.append(f"🏛️ Policy Support: {rec.government_policy}")
            elif "infra" in sector_lower or "construction" in sector_lower:
                rec.government_policy = "Infra capex push, highway projects"
                reasons.append(f"🏛️ Policy Support: {rec.government_policy}")
            elif "green" in sector_lower or "energy" in sector_lower or "renewable" in sector_lower:
                rec.government_policy = "Green energy incentives, PLI schemes"
                reasons.append(f"🏛️ Policy Support: {rec.government_policy}")
            elif "bank" in sector_lower or "financial" in sector_lower:
                rec.government_policy = "Credit growth, banking reforms"
            elif "defence" in sector_lower:
                rec.government_policy = "Make in India defence push, export orders"
                reasons.append(f"🏛️ Defence Boost: {rec.government_policy}")
        
        return rec
