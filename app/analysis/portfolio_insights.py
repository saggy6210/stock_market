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
    
    # Default holdings filename (relative to project root)
    DEFAULT_HOLDINGS_FILE = "holdings.csv"
    
    def __init__(self, holdings_path: str = None):
        """Initialize the portfolio insights generator."""
        if holdings_path:
            self._holdings_path = holdings_path
        else:
            # Find holdings.csv relative to project root
            import os
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self._holdings_path = os.path.join(project_root, self.DEFAULT_HOLDINGS_FILE)
        
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
        Calculate fundamental score (0-100) optimized for medium-term holding (weeks/months).
        
        ENHANCED SCORING FOR MEDIUM-TERM INVESTMENTS:
        
        Quality Metrics (60 points max):
        - ROE > 15% (+20) - Profitability and efficiency
        - Debt/Equity < 1 (+15) - Balance sheet strength
        - Revenue Growth > 10% (+10) - Growth trajectory
        - PE ratio reasonable (+10) - Valuation
        - Profit margin stability (+5) - Business moat
        
        Institutional Support (20 points max):
        - FII holding > 15% (+10) - Smart money confidence
        - FII increasing (+10) - Positive momentum
        
        Risk Adjustment (20 points max):
        - Low volatility bonus (+10)
        - Market cap size (+10) - Large caps safer for medium-term
        
        When no fundamental data:
        - Conservative scoring with sector/position heuristics
        """
        has_fundamental_data = any([
            holding.roe is not None,
            holding.debt_to_equity is not None,
            holding.pe_ratio is not None,
            holding.revenue_growth is not None
        ])
        
        if has_fundamental_data:
            score = 40  # Base score when we have data (more conservative start)
            
            # === QUALITY METRICS (60 points max) ===
            
            # ROE - Key profitability metric for medium-term (max +20)
            if holding.roe:
                if holding.roe > 25:
                    score += 20  # Excellent profitability
                elif holding.roe > 18:
                    score += 15  # Very good
                elif holding.roe > 12:
                    score += 10  # Good
                elif holding.roe > 8:
                    score += 5   # Acceptable
                elif holding.roe < 5:
                    score -= 10  # Poor profitability - risky for medium-term
            
            # Debt to Equity - Balance sheet health crucial for medium-term (max +15)
            if holding.debt_to_equity is not None:
                if holding.debt_to_equity < 0.3:
                    score += 15  # Very strong balance sheet
                elif holding.debt_to_equity < 0.7:
                    score += 10  # Good
                elif holding.debt_to_equity < 1.2:
                    score += 5   # Acceptable
                elif holding.debt_to_equity > 2:
                    score -= 15  # High leverage risk
                elif holding.debt_to_equity > 1.5:
                    score -= 8   # Moderate debt concern
            
            # Revenue Growth - Growth momentum for medium-term (max +10)
            if holding.revenue_growth:
                if holding.revenue_growth > 25:
                    score += 10  # High growth
                elif holding.revenue_growth > 15:
                    score += 8   # Good growth
                elif holding.revenue_growth > 8:
                    score += 5   # Moderate growth
                elif holding.revenue_growth > 0:
                    score += 2   # Positive but low
                elif holding.revenue_growth < -10:
                    score -= 12  # Declining revenue - major red flag
                elif holding.revenue_growth < 0:
                    score -= 6   # Negative growth
            
            # PE Ratio - Valuation check for entry timing (max +10)
            if holding.pe_ratio:
                sector = (holding.sector or "").lower()
                # Sector-adjusted PE thresholds
                if "tech" in sector or "it" in sector:
                    fair_pe_low, fair_pe_high = 15, 35
                elif "bank" in sector or "financial" in sector:
                    fair_pe_low, fair_pe_high = 8, 20
                elif "fmcg" in sector or "consumer" in sector:
                    fair_pe_low, fair_pe_high = 20, 40
                else:
                    fair_pe_low, fair_pe_high = 10, 25  # Default
                
                if fair_pe_low <= holding.pe_ratio <= fair_pe_high:
                    score += 10  # Fairly valued
                elif holding.pe_ratio < fair_pe_low:
                    # Low PE - could be value or value trap
                    if holding.revenue_growth and holding.revenue_growth > 5:
                        score += 8  # Undervalued with growth
                    else:
                        score += 3  # Potential value trap
                elif holding.pe_ratio > fair_pe_high * 1.5:
                    score -= 8  # Very expensive
                elif holding.pe_ratio > fair_pe_high:
                    score -= 4  # Somewhat expensive
            
            # === INSTITUTIONAL SUPPORT (20 points max) ===
            
            if holding.fii_holding_pct:
                if holding.fii_holding_pct > 25:
                    score += 10  # High institutional interest
                elif holding.fii_holding_pct > 15:
                    score += 7
                elif holding.fii_holding_pct > 8:
                    score += 4
            
            if holding.fii_change:
                if holding.fii_change > 2:
                    score += 10  # FII accumulating
                elif holding.fii_change > 0.5:
                    score += 6
                elif holding.fii_change < -2:
                    score -= 8  # FII selling - bearish signal
                elif holding.fii_change < -0.5:
                    score -= 4
            
            # === RISK ADJUSTMENT (max +10) ===
            
            # Market cap consideration (larger = safer for medium-term)
            # Use investment amount as proxy for market cap exposure
            if holding.investment > 50000:
                score += 5  # Likely large cap holding
            elif holding.investment > 20000:
                score += 3
            
        else:
            # No fundamental data - use conservative heuristics
            score = 45  # Start lower without data (more conservative)
            
            # Sector-based scoring (some sectors safer for medium-term)
            sector = (holding.sector or "").lower()
            if any(s in sector for s in ["bank", "financial", "it", "tech", "pharma", "fmcg"]):
                score += 10  # Established sectors
            elif any(s in sector for s in ["infra", "industrial", "auto"]):
                score += 5   # Cyclical but established
            elif any(s in sector for s in ["micro", "small", "penny"]):
                score -= 10  # Higher risk small/micro caps
            
            # Position health indicators
            if holding.pnl_pct > 0:
                score += 8   # Profitable position suggests quality
            elif holding.pnl_pct > -15:
                score += 4
            elif holding.pnl_pct < -50:
                score -= 12  # Very deep loss is concerning
            elif holding.pnl_pct < -30:
                score -= 5
            
            # Portfolio weight as quality proxy
            if holding.portfolio_weight > 5:
                score += 8   # Significant allocation = likely quality
            elif holding.portfolio_weight > 2:
                score += 4
            elif holding.portfolio_weight < 0.5:
                score -= 3   # Very small position = potentially speculative
            
            # Day change shows current market sentiment
            if holding.day_change_pct > 4:
                score += 5   # Strong momentum
            elif holding.day_change_pct > 2:
                score += 3
            elif holding.day_change_pct < -4:
                score -= 5   # Weak sentiment
        
        # === TECHNICAL HEALTH ADJUSTMENT ===
        
        if holding.rsi:
            # RSI for medium-term: prefer stocks not at extremes
            if 45 <= holding.rsi <= 55:
                score += 8   # Neutral zone - good entry for medium-term
            elif 35 <= holding.rsi <= 65:
                score += 5   # Acceptable range
            elif holding.rsi < 25:
                score += 3   # Deeply oversold - potential bounce but risky
            elif holding.rsi < 35:
                score += 5   # Oversold - good accumulation zone
            elif holding.rsi > 75:
                score -= 8   # Very overbought - not ideal entry
            elif holding.rsi > 65:
                score -= 3   # Somewhat expensive technically
        
        # Trend alignment bonus for medium-term
        if hasattr(holding, 'trend'):
            if holding.trend == "Uptrend":
                score += 5   # Trend following works for medium-term
            elif holding.trend == "Downtrend":
                score -= 5   # Fighting the trend is risky
        
        return max(0, min(100, score))
    
    def _generate_signal(self, holding: HoldingAnalysis) -> None:
        """
        Generate Buy/Hold/Sell signal for a holding optimized for MEDIUM-TERM (weeks/months).
        
        KEY PRINCIPLES FOR MEDIUM-TERM SIGNALS:
        1. Focus on fundamental quality over short-term price moves
        2. Consider valuation attractiveness (decline from cost)
        3. Account for sector/market cycles
        4. Prioritize risk-adjusted returns
        5. Factor in institutional positioning
        
        Signal Meanings:
        - AGGRESSIVE BUY: High conviction, average aggressively (2-3x position size over weeks)
        - BUY ON DIP: Good opportunity, add 25-50% on further weakness
        - HOLD: Maintain position, no action needed
        - REDUCE: Take partial profits or reduce exposure by 25-50%
        - EXIT: Complete exit recommended over 2-4 weeks
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
        
        # Technical context
        is_oversold = holding.rsi and holding.rsi < 35
        is_overbought = holding.rsi and holding.rsi > 65
        in_uptrend = hasattr(holding, 'trend') and holding.trend == "Uptrend"
        in_downtrend = hasattr(holding, 'trend') and holding.trend == "Downtrend"
        
        # === STRONG FUNDAMENTALS (Score >= 70) ===
        if score >= 70:
            if pnl_pct < -35 and is_oversold:
                holding.signal = PortfolioSignal.AGGRESSIVE_BUY
                reasons.append("💎 Premium quality at deep discount - aggressive accumulation zone")
                reasons.append(f"Down {abs(pnl_pct):.0f}% with strong fundamentals")
            elif pnl_pct < -25:
                holding.signal = PortfolioSignal.AGGRESSIVE_BUY
                reasons.append("Strong fundamentals at attractive valuation")
                reasons.append("Ideal for systematic accumulation over weeks")
            elif pnl_pct < -10:
                holding.signal = PortfolioSignal.BUY_ON_DIP
                reasons.append("Quality stock, add on further weakness")
            elif pnl_pct > 40 and is_overbought:
                holding.signal = PortfolioSignal.REDUCE
                reasons.append("Strong gains, consider partial profit booking")
            else:
                holding.signal = PortfolioSignal.HOLD
                reasons.append("Core holding, maintain for long-term wealth creation")
            
            # Add specific fundamental highlights
            if holding.roe and holding.roe > 18:
                reasons.append(f"Excellent capital efficiency (ROE: {holding.roe:.1f}%)")
            if holding.debt_to_equity is not None and holding.debt_to_equity < 0.5:
                reasons.append("Strong balance sheet, low leverage risk")
            if holding.revenue_growth and holding.revenue_growth > 15:
                reasons.append(f"Healthy growth trajectory ({holding.revenue_growth:.0f}% revenue growth)")
                
        # === GOOD FUNDAMENTALS (Score 55-70) ===
        elif score >= 55:
            if pnl_pct < -40 and is_oversold:
                holding.signal = PortfolioSignal.BUY_ON_DIP
                reasons.append("Good fundamentals at significant discount")
                if not has_fundamental_data:
                    reasons.append("⚠️ Verify fundamentals before averaging")
            elif pnl_pct < -25:
                holding.signal = PortfolioSignal.BUY_ON_DIP
                reasons.append("Reasonable entry point for medium-term")
            elif pnl_pct < -10:
                holding.signal = PortfolioSignal.HOLD
                reasons.append("Decent fundamentals, hold through correction")
            elif pnl_pct > 25 and is_overbought:
                holding.signal = PortfolioSignal.REDUCE
                reasons.append("Book partial profits, maintain core position")
            elif pnl_pct > 35:
                holding.signal = PortfolioSignal.REDUCE
                reasons.append("Extended gains, trim 25-30% to lock profits")
            else:
                holding.signal = PortfolioSignal.HOLD
                reasons.append("Maintain position, monitor quarterly results")
                
        # === AVERAGE FUNDAMENTALS (Score 45-55) ===
        elif score >= 45:
            if pnl_pct < -50:
                holding.signal = PortfolioSignal.REDUCE
                reasons.append("Very deep loss with average fundamentals")
                reasons.append("Consider reducing on bounce to redeploy capital")
            elif pnl_pct < -30:
                holding.signal = PortfolioSignal.HOLD
                reasons.append("Hold but set strict review timeline (4-6 weeks)")
                reasons.append("Exit if no fundamental improvement seen")
            elif pnl_pct > 20:
                holding.signal = PortfolioSignal.REDUCE
                reasons.append("Book profits in average-quality stock")
            else:
                holding.signal = PortfolioSignal.HOLD
                reasons.append("Watchlist candidate - monitor closely")
                
        # === WEAK FUNDAMENTALS (Score < 45) ===
        else:
            if pnl_pct < -60:
                holding.signal = PortfolioSignal.EXIT
                reasons.append("🚨 Weak fundamentals + severe loss - exit priority")
                reasons.append("Redeploy capital to quality stocks")
            elif pnl_pct < -40:
                holding.signal = PortfolioSignal.EXIT
                reasons.append("Quality concerns with deep loss - exit on bounce")
                reasons.append("Capital better deployed elsewhere")
            elif pnl_pct < -25:
                holding.signal = PortfolioSignal.REDUCE
                reasons.append("Weak fundamentals, reduce exposure gradually")
            elif pnl_pct > 10:
                holding.signal = PortfolioSignal.REDUCE
                reasons.append("Book profits in weak fundamental stock")
            else:
                holding.signal = PortfolioSignal.HOLD
                reasons.append("⚠️ Monitor closely, prepare exit plan")
            
            if holding.debt_to_equity and holding.debt_to_equity > 2:
                reasons.append(f"⚠️ High debt risk (D/E: {holding.debt_to_equity:.1f})")
            if in_downtrend:
                reasons.append("Technical downtrend adding to risk")
        
        # === TECHNICAL OVERLAY FOR TIMING ===
        if holding.signal in [PortfolioSignal.AGGRESSIVE_BUY, PortfolioSignal.BUY_ON_DIP]:
            if is_oversold:
                reasons.append(f"📊 RSI oversold ({holding.rsi:.0f}) - good entry timing")
            if in_uptrend:
                reasons.append("📈 Uptrend intact - momentum supportive")
        
        if holding.signal in [PortfolioSignal.REDUCE, PortfolioSignal.EXIT]:
            if is_overbought:
                reasons.append("📉 RSI overbought - good exit timing")
            if in_downtrend:
                reasons.append("⬇️ Downtrend - accelerate exit plan")
        
        # === RISK LEVEL ASSESSMENT ===
        if score >= 70 and (holding.debt_to_equity is None or holding.debt_to_equity < 1):
            holding.risk_level = RiskLevel.LOW
        elif score >= 55 and (holding.debt_to_equity is None or holding.debt_to_equity < 1.5):
            holding.risk_level = RiskLevel.MEDIUM
        elif score >= 40:
            holding.risk_level = RiskLevel.HIGH
        else:
            holding.risk_level = RiskLevel.VERY_HIGH
        
        # Adjust risk for position size
        if holding.portfolio_weight > 10:
            holding.risk_level = RiskLevel(min(holding.risk_level.value, RiskLevel.MEDIUM.value))
            reasons.append("⚠️ Position concentration risk")
        
        # Confidence calculation
        base_confidence = holding.fundamental_score
        # Boost confidence if technical confirms fundamental view
        if (score >= 60 and is_oversold) or (score < 40 and is_overbought):
            base_confidence += 10
        holding.confidence = min(90, base_confidence + 5)
        holding.reasons = reasons[:6]
    
    def _generate_prediction(self, holding: HoldingAnalysis) -> None:
        """
        Generate medium-term (weeks/months) movement prediction.
        
        IMPROVED PREDICTION LOGIC FOR MEDIUM-TERM:
        
        Factors considered (weighted scoring):
        1. Fundamental Score (40% weight) - Quality of the business
        2. Technical Position (25% weight) - RSI, trend, support/resistance
        3. P&L Recovery Potential (20% weight) - Mean reversion opportunity
        4. Institutional Interest (15% weight) - Smart money positioning
        
        Confidence calibration:
        - Base confidence: 50%
        - Adjustments based on factor alignment
        - Capped at 85% (acknowledging market uncertainty)
        """
        # Initialize scores
        fundamental_signal = 0  # -100 to +100
        technical_signal = 0
        recovery_signal = 0
        institutional_signal = 0
        
        reasons = []
        
        # === FUNDAMENTAL ANALYSIS (40% weight) ===
        if holding.fundamental_score >= 75:
            fundamental_signal = 60
            reasons.append("Strong business fundamentals support upside")
        elif holding.fundamental_score >= 60:
            fundamental_signal = 35
            reasons.append("Good fundamentals favor medium-term growth")
        elif holding.fundamental_score >= 45:
            fundamental_signal = 10
            reasons.append("Moderate fundamentals, limited conviction")
        elif holding.fundamental_score >= 30:
            fundamental_signal = -20
            reasons.append("Weak fundamentals suggest continued pressure")
        else:
            fundamental_signal = -50
            reasons.append("Poor fundamentals, high downside risk")
        
        # === TECHNICAL ANALYSIS (25% weight) ===
        
        # RSI analysis for medium-term
        if holding.rsi:
            if holding.rsi < 25:
                technical_signal += 35
                reasons.append(f"Deeply oversold (RSI {holding.rsi:.0f}), strong bounce potential")
            elif holding.rsi < 35:
                technical_signal += 25
                reasons.append(f"Oversold (RSI {holding.rsi:.0f}), accumulation zone")
            elif holding.rsi < 45:
                technical_signal += 10
                reasons.append("RSI in neutral-bullish zone")
            elif holding.rsi > 80:
                technical_signal -= 30
                reasons.append(f"Extremely overbought (RSI {holding.rsi:.0f}), pullback likely")
            elif holding.rsi > 70:
                technical_signal -= 15
                reasons.append(f"Overbought (RSI {holding.rsi:.0f}), consolidation expected")
            elif holding.rsi > 60:
                technical_signal -= 5
        
        # Trend analysis
        if hasattr(holding, 'trend') and holding.trend:
            if holding.trend == "Uptrend":
                technical_signal += 20
                reasons.append("Technical uptrend intact, momentum favorable")
            elif holding.trend == "Downtrend":
                technical_signal -= 20
                reasons.append("Technical downtrend, wait for reversal signal")
        
        # Support proximity (good entry for medium-term)
        if holding.support and holding.current_price > 0:
            support_distance = ((holding.current_price - holding.support) / holding.current_price) * 100
            if support_distance < 5:
                technical_signal += 15
                reasons.append(f"Trading near strong support (₹{holding.support:.2f})")
            elif support_distance > 20:
                technical_signal -= 5  # Far from support
        
        # === MEAN REVERSION / RECOVERY POTENTIAL (20% weight) ===
        
        if holding.pnl_pct < -50 and holding.fundamental_score >= 55:
            recovery_signal = 50
            reasons.append("Significant mean reversion potential with decent fundamentals")
        elif holding.pnl_pct < -40 and holding.fundamental_score >= 50:
            recovery_signal = 40
            reasons.append("Deep discount to cost, recovery probable")
        elif holding.pnl_pct < -30 and holding.fundamental_score >= 45:
            recovery_signal = 30
            reasons.append("Substantial decline creates opportunity")
        elif holding.pnl_pct < -20 and holding.fundamental_score >= 45:
            recovery_signal = 20
            reasons.append("Moderate pullback, accumulation opportunity")
        elif holding.pnl_pct < -10:
            recovery_signal = 10
        elif holding.pnl_pct > 30:
            recovery_signal = -15  # Extended gains, profit booking risk
            reasons.append("Extended gains, partial profit booking possible")
        elif holding.pnl_pct > 20:
            recovery_signal = -10
        
        # === INSTITUTIONAL SIGNAL (15% weight) ===
        
        if holding.fii_change:
            if holding.fii_change > 3:
                institutional_signal = 40
                reasons.append("Strong FII accumulation ongoing")
            elif holding.fii_change > 1:
                institutional_signal = 25
                reasons.append("FII buying, institutional support")
            elif holding.fii_change > 0:
                institutional_signal = 10
            elif holding.fii_change < -3:
                institutional_signal = -35
                reasons.append("FII selling pressure, caution warranted")
            elif holding.fii_change < -1:
                institutional_signal = -20
                reasons.append("FII reducing exposure")
        elif holding.fii_holding_pct:
            if holding.fii_holding_pct > 30:
                institutional_signal = 20
            elif holding.fii_holding_pct > 15:
                institutional_signal = 10
            elif holding.fii_holding_pct < 5:
                institutional_signal = -10
        
        # === CALCULATE WEIGHTED DIRECTION ===
        
        total_signal = (
            fundamental_signal * 0.40 +
            technical_signal * 0.25 +
            recovery_signal * 0.20 +
            institutional_signal * 0.15
        )
        
        # === DETERMINE DIRECTION AND CONFIDENCE ===
        
        if total_signal > 25:
            holding.predicted_direction = "UP"
            # Confidence scales with signal strength
            base_confidence = 55 + (total_signal - 25) * 0.5
            # Boost confidence if multiple factors align
            factor_count = sum([
                fundamental_signal > 20,
                technical_signal > 10,
                recovery_signal > 15,
                institutional_signal > 10
            ])
            confidence_boost = factor_count * 5
            holding.predicted_confidence = min(85, base_confidence + confidence_boost)
        elif total_signal < -20:
            holding.predicted_direction = "DOWN"
            base_confidence = 55 + abs(total_signal + 20) * 0.4
            factor_count = sum([
                fundamental_signal < -15,
                technical_signal < -10,
                recovery_signal < -5,
                institutional_signal < -10
            ])
            confidence_boost = factor_count * 4
            holding.predicted_confidence = min(80, base_confidence + confidence_boost)
        else:
            holding.predicted_direction = "SIDEWAYS"
            holding.predicted_confidence = 50 + abs(total_signal) * 0.3
        
        # === SET PREDICTION REASON (pick best reason) ===
        
        # Prioritize reasons by importance
        reason_priorities = [
            "Deeply oversold", "Strong FII accumulation", "Significant mean reversion",
            "Strong business fundamentals", "Technical uptrend", "FII selling",
            "Poor fundamentals", "Extremely overbought", "Trading near strong support"
        ]
        
        primary_reason = reasons[0] if reasons else "Mixed signals, sideways expected"
        for priority in reason_priorities:
            for r in reasons:
                if priority.lower() in r.lower():
                    primary_reason = r
                    break
            else:
                continue
            break
        
        holding.prediction_reason = primary_reason
    
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
        Generate top 10 detailed buy recommendations for MEDIUM-TERM holding (weeks/months).
        
        IMPROVED SELECTION CRITERIA:
        1. Minimum fundamental score of 55 (quality threshold)
        2. Meaningful decline (-15% or more) for value opportunity
        3. Reasonable position size for averaging
        4. Diversification across sectors
        
        RANKING ALGORITHM:
        - Composite score = (Fundamental Score * 0.5) + (Discount Factor * 0.3) + (Sector Bonus * 0.2)
        - Discount Factor: More discount = higher score (capped at 50% decline)
        - Sector Bonus: Favor underrepresented quality sectors
        """
        recommendations = []
        
        # Filter for strong buy candidates with stricter criteria
        candidates = [
            h for h in holdings
            if h.signal in [PortfolioSignal.AGGRESSIVE_BUY, PortfolioSignal.BUY_ON_DIP]
            and h.fundamental_score >= 55  # Higher threshold for medium-term
            and h.pnl_pct < -10  # Must have meaningful discount
        ]
        
        # Calculate composite score for ranking
        def calc_composite_score(h: HoldingAnalysis) -> float:
            # Fundamental score (50% weight)
            fund_component = h.fundamental_score * 0.5
            
            # Discount factor (30% weight) - deeper discount = higher score
            # Cap at 50% decline, normalize to 0-100
            discount_pct = min(abs(h.pnl_pct), 50)
            discount_component = (discount_pct / 50) * 100 * 0.3
            
            # Technical timing bonus (10% weight)
            tech_component = 0
            if h.rsi and h.rsi < 35:
                tech_component = 25  # Oversold bonus
            elif h.rsi and h.rsi < 45:
                tech_component = 15  # Neutral-bullish
            elif h.rsi and h.rsi > 65:
                tech_component = -10  # Overbought penalty
            tech_component *= 0.1
            
            # Position size factor (10% weight) - prefer larger positions for averaging
            size_component = 0
            if h.investment > 30000:
                size_component = 20
            elif h.investment > 15000:
                size_component = 15
            elif h.investment > 5000:
                size_component = 10
            else:
                size_component = 5  # Small position, less averaging benefit
            size_component *= 0.1
            
            return fund_component + discount_component + tech_component + size_component
        
        # Sort by composite score
        candidates.sort(key=calc_composite_score, reverse=True)
        
        # Diversification: limit to 2 stocks per sector
        sector_counts = {}
        selected = []
        for h in candidates:
            sector = h.sector or "Unknown"
            if sector_counts.get(sector, 0) < 2:
                selected.append(h)
                sector_counts[sector] = sector_counts.get(sector, 0) + 1
                if len(selected) >= 10:
                    break
        
        for holding in selected:
            rec = self._build_detailed_recommendation(holding, news_items)
            recommendations.append(rec)
        
        return recommendations
    
    def _build_detailed_recommendation(
        self,
        holding: HoldingAnalysis,
        news_items: list[NewsItem]
    ) -> DetailedBuyRecommendation:
        """
        Build a detailed recommendation for medium-term holding (weeks/months).
        
        Includes:
        - Suggested holding period based on decline and fundamentals
        - Phased buying recommendation (not all at once)
        - Risk-adjusted position sizing
        - Clear target and stop-loss levels
        """
        rec = DetailedBuyRecommendation(
            symbol=holding.symbol,
            company_name=holding.company_name,
            sector=holding.sector,
            current_price=holding.current_price,
            current_holding_qty=holding.quantity,
            current_avg_cost=holding.avg_cost,
        )
        
        # === POSITION SIZING BASED ON FUNDAMENTAL QUALITY AND DECLINE ===
        current_investment = holding.investment
        
        # Quality-adjusted position sizing
        if holding.fundamental_score >= 70:
            # High quality - can be more aggressive
            if holding.pnl_pct < -40:
                rec.recommended_investment = current_investment * 0.6  # 60% of position
                rec.signal = "AGGRESSIVE BUY"
            elif holding.pnl_pct < -25:
                rec.recommended_investment = current_investment * 0.4
                rec.signal = "STRONG BUY"
            else:
                rec.recommended_investment = current_investment * 0.25
                rec.signal = "BUY ON DIP"
        elif holding.fundamental_score >= 55:
            # Medium quality - moderate sizing
            if holding.pnl_pct < -35:
                rec.recommended_investment = current_investment * 0.35
                rec.signal = "STRONG BUY"
            elif holding.pnl_pct < -20:
                rec.recommended_investment = current_investment * 0.25
                rec.signal = "BUY ON DIP"
            else:
                rec.recommended_investment = current_investment * 0.15
                rec.signal = "SMALL ADD"
        else:
            # Lower quality - conservative
            rec.recommended_investment = current_investment * 0.15
            rec.signal = "CAUTIOUS BUY"
        
        # Cap based on risk management (max ₹75K for high quality, ₹40K for others)
        max_investment = 75000 if holding.fundamental_score >= 70 else 40000
        rec.recommended_investment = min(rec.recommended_investment, max_investment)
        
        # Calculate quantity
        if holding.current_price > 0:
            rec.recommended_qty = int(rec.recommended_investment / holding.current_price)
            rec.recommended_investment = rec.recommended_qty * holding.current_price
        
        # Entry range - widen for high volatility stocks (using day change as proxy)
        volatility_factor = max(3, min(8, abs(holding.day_change_pct) * 1.5 + 3))
        rec.entry_price_range = (
            f"₹{holding.current_price * (1 - volatility_factor/100):.2f} - "
            f"₹{holding.current_price * (1 + volatility_factor/100):.2f}"
        )
        
        # === MEDIUM-TERM TARGETS (optimized for weeks/months holding) ===
        
        # Target based on fundamentals and decline
        if holding.pnl_pct < -40 and holding.fundamental_score >= 65:
            # Deep value: expect 30-40% recovery over 3-6 months
            rec.target_price = holding.current_price * 1.35
        elif holding.pnl_pct < -25 and holding.fundamental_score >= 60:
            # Good value: expect 20-30% over 2-4 months
            rec.target_price = holding.current_price * 1.25
        elif holding.pnl_pct < -15:
            # Moderate discount: expect 15-20% over 1-3 months
            rec.target_price = holding.current_price * 1.18
        else:
            # Small discount: expect 10-15% over 1-2 months
            rec.target_price = holding.current_price * 1.12
        
        # Override with technical resistance if available
        if holding.resistance and holding.resistance > holding.current_price:
            rec.target_price = max(rec.target_price, holding.resistance)
        
        # Stop-loss based on support or percentage
        if holding.support and holding.support < holding.current_price:
            # Use 5% below support
            rec.stop_loss = holding.support * 0.95
        else:
            # Default: 12% below current for medium-term
            rec.stop_loss = holding.current_price * 0.88
        
        rec.expected_return_pct = ((rec.target_price - holding.current_price) / holding.current_price) * 100
        
        # Decline metrics
        rec.decline_from_high = holding.pnl_pct
        rec.decline_from_feb28 = holding.decline_from_feb28 or 0
        rec.decline_from_jan1 = holding.decline_from_jan1 or 0
        
        # === SCORING ===
        rec.fundamental_score = holding.fundamental_score
        
        # Technical score with more nuanced calculation
        rec.technical_score = 50  # Base score
        if holding.rsi:
            if holding.rsi < 25:
                rec.technical_score += 35  # Deeply oversold
            elif holding.rsi < 35:
                rec.technical_score += 25
            elif holding.rsi < 45:
                rec.technical_score += 10
            elif holding.rsi > 70:
                rec.technical_score -= 15
        
        if holding.trend == "Uptrend":
            rec.technical_score += 15
        elif holding.trend == "Downtrend":
            rec.technical_score -= 10
        
        rec.overall_confidence = (rec.fundamental_score * 0.6 + rec.technical_score * 0.4)
        
        # === GENERATE DETAILED REASONS ===
        reasons = []
        
        # FII/DII activity (high priority for medium-term)
        if holding.fii_change and holding.fii_change > 1:
            rec.fii_dii_activity = f"FII increased stake by {holding.fii_change:.1f}% last quarter"
            reasons.append(f"📈 Smart Money: {rec.fii_dii_activity}")
        elif holding.fii_change and holding.fii_change > 0:
            rec.fii_dii_activity = f"FII marginally increased ({holding.fii_change:.1f}%)"
            reasons.append(f"🏦 {rec.fii_dii_activity}")
        elif holding.fii_holding_pct and holding.fii_holding_pct > 25:
            rec.fii_dii_activity = f"Strong FII base: {holding.fii_holding_pct:.1f}%"
            reasons.append(f"🏦 Institutional Support: {rec.fii_dii_activity}")
        
        # Fundamental quality reasons
        if holding.roe and holding.roe > 18:
            rec.earnings_profit = f"Excellent capital efficiency (ROE: {holding.roe:.1f}%)"
            reasons.append(f"💰 {rec.earnings_profit}")
        elif holding.roe and holding.roe > 12:
            rec.earnings_profit = f"Good ROE of {holding.roe:.1f}%"
            reasons.append(f"💰 {rec.earnings_profit}")
        
        if holding.revenue_growth and holding.revenue_growth > 15:
            reasons.append(f"📊 Strong growth: {holding.revenue_growth:.1f}% revenue increase")
        elif holding.revenue_growth and holding.revenue_growth > 8:
            reasons.append(f"📊 Steady growth: {holding.revenue_growth:.1f}% revenue increase")
        
        if holding.debt_to_equity is not None and holding.debt_to_equity < 0.3:
            reasons.append(f"🛡️ Very low debt (D/E: {holding.debt_to_equity:.2f}) - safe for medium-term")
        elif holding.debt_to_equity is not None and holding.debt_to_equity < 0.7:
            reasons.append(f"🛡️ Manageable debt (D/E: {holding.debt_to_equity:.2f})")
        
        # Valuation reasons
        if holding.pe_ratio:
            sector = (holding.sector or "").lower()
            if "tech" in sector or "it" in sector:
                if holding.pe_ratio < 25:
                    reasons.append(f"📉 Attractive tech valuation (PE: {holding.pe_ratio:.1f})")
            elif "bank" in sector or "financial" in sector:
                if holding.pe_ratio < 15:
                    reasons.append(f"📉 Value pricing for financials (PE: {holding.pe_ratio:.1f})")
            elif holding.pe_ratio < 20:
                reasons.append(f"📉 Reasonable valuation (PE: {holding.pe_ratio:.1f})")
        
        # Technical timing reasons
        if holding.rsi and holding.rsi < 30:
            rec.technical_reason = f"Deeply oversold (RSI: {holding.rsi:.0f}) - strong bounce potential"
            reasons.append(f"📊 {rec.technical_reason}")
        elif holding.rsi and holding.rsi < 40:
            rec.technical_reason = f"Oversold zone (RSI: {holding.rsi:.0f}) - accumulation area"
            reasons.append(f"📊 {rec.technical_reason}")
        
        if holding.trend == "Uptrend":
            reasons.append("📈 Technical uptrend - momentum supportive")
        
        # Discount-based reasons (key for medium-term value)
        if holding.pnl_pct < -40:
            reasons.append(f"💎 DEEP VALUE: Down {abs(holding.pnl_pct):.0f}% - significant recovery potential")
        elif holding.pnl_pct < -25:
            reasons.append(f"💎 VALUE: Down {abs(holding.pnl_pct):.0f}% from cost - attractive entry")
        
        # Default reasons if none found
        if not reasons:
            reasons = [
                "Strong sector positioning for medium-term",
                "Quality business with growth runway",
                "Market correction creates opportunity"
            ]
        
        rec.reasons = reasons[:6]
        
        # Related news (important for medium-term catalyst)
        symbol_upper = holding.symbol.upper()
        for news in news_items[:15]:
            if symbol_upper in news.headline.upper() or symbol_upper in [s.upper() for s in news.stocks_mentioned]:
                # Prioritize positive news
                if news.sentiment == "positive" or len(rec.related_news) < 2:
                    rec.related_news.append(news.headline[:80])
                    if len(rec.related_news) >= 3:
                        break
        
        # Sector/policy catalyst (important for medium-term thesis)
        if holding.sector:
            sector_lower = holding.sector.lower()
            if "tech" in sector_lower or "it" in sector_lower:
                rec.government_policy = "Digital India, AI/Cloud adoption, IT export growth"
            elif "infra" in sector_lower or "construction" in sector_lower:
                rec.government_policy = "PM Gati Shakti, ₹10L Cr Infra push, highway projects"
            elif "green" in sector_lower or "energy" in sector_lower or "renewable" in sector_lower:
                rec.government_policy = "500 GW renewable by 2030, PLI for solar, EV incentives"
            elif "bank" in sector_lower or "financial" in sector_lower:
                rec.government_policy = "Credit growth, NPA cleanup, financial inclusion"
            elif "defence" in sector_lower:
                rec.government_policy = "Atmanirbhar Bharat, defence exports, modernization"
            elif "pharma" in sector_lower or "health" in sector_lower:
                rec.government_policy = "Healthcare expansion, API self-reliance, Ayushman"
            elif "auto" in sector_lower:
                rec.government_policy = "EV transition, FAME subsidies, export growth"
        
        return rec
