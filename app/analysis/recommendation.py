"""
Recommendation Engine.
Generates buy/sell recommendations based on technical analysis and news sentiment.

OPTIMIZED FOR MEDIUM-TERM HOLDING (weeks/months):
- Reduced weight on short-term momentum indicators
- Increased weight on trend and valuation
- News sentiment captures market perception
"""

import logging
from typing import Optional

from app.data.models import (
    StockSnapshot, StockRecommendation, TechnicalIndicators,
    Signal, Trend, RiskLevel,
)
from app.analysis.news_sentiment import NewsSentimentAnalyzer, NewsSentiment

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Generate stock recommendations based on analysis for medium-term holding."""
    
    # Score weights optimized for medium-term (weeks/months) holding
    # Reduced short-term factors, increased fundamental/trend factors
    WEIGHTS = {
        "technical": 0.25,     # Price vs moving averages, bollinger bands
        "trend": 0.30,         # Trend strength and direction (most important for medium-term)
        "momentum": 0.10,      # RSI, MACD (reduced weight - less relevant for medium-term)
        "volume": 0.10,        # Volume patterns (reduced weight)
        "sentiment": 0.15,     # News sentiment
        "valuation": 0.10,     # PE ratio assessment (new for medium-term)
    }
    
    def __init__(self):
        """Initialize the recommendation engine."""
        self._news_analyzer = NewsSentimentAnalyzer()
    
    def analyze(
        self,
        stock: StockSnapshot,
        indicators: TechnicalIndicators,
        avg_volume: Optional[float] = None,
        include_news: bool = True,
    ) -> StockRecommendation:
        """
        Generate recommendation for a stock.
        
        Args:
            stock: Stock snapshot
            indicators: Technical indicators
            avg_volume: Average volume for comparison
            include_news: Whether to include news sentiment analysis
            
        Returns:
            StockRecommendation: Generated recommendation
        """
        # Get news sentiment
        sentiment = None
        sentiment_score = 50  # Default neutral
        if include_news:
            try:
                sentiment = self._news_analyzer.get_stock_sentiment(stock.symbol)
                # Convert -1 to 1 range to 0 to 100
                sentiment_score = (sentiment.sentiment_score + 1) * 50
            except Exception as e:
                logger.debug(f"Failed to get sentiment for {stock.symbol}: {e}")
        
        # Calculate component scores
        technical_score = self._calc_technical_score(stock, indicators)
        trend_score = self._calc_trend_score(indicators)
        momentum_score = self._calc_momentum_score(indicators)
        volume_score = self._calc_volume_score(stock, avg_volume)
        valuation_score = self._calc_valuation_score(stock)  # New for medium-term
        
        # Calculate overall score with all components (medium-term optimized weights)
        overall_score = (
            technical_score * self.WEIGHTS["technical"]
            + trend_score * self.WEIGHTS["trend"]
            + momentum_score * self.WEIGHTS["momentum"]
            + volume_score * self.WEIGHTS["volume"]
            + sentiment_score * self.WEIGHTS["sentiment"]
            + valuation_score * self.WEIGHTS["valuation"]
        )
        
        # Determine signal
        signal = self._determine_signal(overall_score)
        
        # Calculate targets (medium-term focused)
        target_price, stop_loss = self._calc_targets(stock, indicators, signal)
        expected_return = ((target_price - stock.price) / stock.price * 100) if stock.price > 0 else 0
        
        # Determine risk level
        risk_level = self._determine_risk(stock, indicators)
        
        # Generate reasons including news sentiment
        reasons = self._generate_reasons(stock, indicators, signal, sentiment)
        
        # MACD signal string
        macd_signal_str = ""
        if indicators.macd_histogram is not None:
            macd_signal_str = "Bullish" if indicators.macd_histogram > 0 else "Bearish"
        
        return StockRecommendation(
            symbol=stock.symbol,
            company_name=stock.company_name,
            sector=stock.sector,
            segment=stock.segment,
            current_price=stock.price,
            target_price=target_price,
            stop_loss=stop_loss,
            expected_return=expected_return,
            overall_score=overall_score,
            technical_score=technical_score,
            trend_score=trend_score,
            momentum_score=momentum_score,
            volume_score=volume_score,
            signal=signal,
            risk_level=risk_level,
            confidence=min(overall_score, 100),
            rsi=indicators.rsi,
            trend=indicators.trend,
            macd_signal=macd_signal_str,
            reasons=reasons,
        )
    
    def _calc_technical_score(
        self,
        stock: StockSnapshot,
        indicators: TechnicalIndicators,
    ) -> float:
        """Calculate technical score (0-100)."""
        score = 50  # Base score
        
        if not stock.price:
            return score
        
        # SMA signals
        if indicators.sma_20 and stock.price > indicators.sma_20:
            score += 10
        elif indicators.sma_20:
            score -= 10
        
        if indicators.sma_50 and stock.price > indicators.sma_50:
            score += 10
        elif indicators.sma_50:
            score -= 10
        
        if indicators.sma_200 and stock.price > indicators.sma_200:
            score += 10
        elif indicators.sma_200:
            score -= 10
        
        # Bollinger Band position
        if indicators.bollinger_lower and stock.price < indicators.bollinger_lower:
            score += 10  # Oversold
        elif indicators.bollinger_upper and stock.price > indicators.bollinger_upper:
            score -= 10  # Overbought
        
        return max(0, min(100, score))
    
    def _calc_trend_score(self, indicators: TechnicalIndicators) -> float:
        """Calculate trend score (0-100)."""
        trend_scores = {
            Trend.STRONG_UPTREND: 100,
            Trend.UPTREND: 75,
            Trend.SIDEWAYS: 50,
            Trend.DOWNTREND: 25,
            Trend.STRONG_DOWNTREND: 0,
        }
        
        base_score = trend_scores.get(indicators.trend, 50)
        
        # ADX adjustment
        if indicators.adx:
            if indicators.adx > 50:
                adjustment = 10 if indicators.trend in [Trend.UPTREND, Trend.STRONG_UPTREND] else -10
            elif indicators.adx > 25:
                adjustment = 5 if indicators.trend in [Trend.UPTREND, Trend.STRONG_UPTREND] else -5
            else:
                adjustment = 0
            base_score += adjustment
        
        return max(0, min(100, base_score))
    
    def _calc_momentum_score(self, indicators: TechnicalIndicators) -> float:
        """Calculate momentum score (0-100)."""
        score = 50
        
        # RSI contribution
        if indicators.rsi is not None:
            if indicators.rsi < 30:
                score += 30  # Oversold - bullish
            elif indicators.rsi < 40:
                score += 15
            elif indicators.rsi > 70:
                score -= 30  # Overbought - bearish
            elif indicators.rsi > 60:
                score -= 15
        
        # MACD contribution
        if indicators.macd_histogram is not None:
            if indicators.macd_histogram > 0:
                score += 15
            else:
                score -= 15
        
        return max(0, min(100, score))
    
    def _calc_volume_score(
        self,
        stock: StockSnapshot,
        avg_volume: Optional[float],
    ) -> float:
        """Calculate volume score (0-100)."""
        if not avg_volume or not stock.volume:
            return 50
        
        volume_ratio = stock.volume / avg_volume
        
        # Higher volume with price increase is bullish
        if stock.change_pct > 0:
            if volume_ratio > 2:
                return 90
            elif volume_ratio > 1.5:
                return 75
            elif volume_ratio > 1:
                return 60
        else:
            if volume_ratio > 2:
                return 20  # High volume selling
            elif volume_ratio > 1.5:
                return 35
        
        return 50
    
    def _calc_valuation_score(self, stock: StockSnapshot) -> float:
        """
        Calculate valuation score based on P/E ratio with sector adjustment.
        
        Sector-aware PE thresholds for more accurate valuation assessment:
        - Tech/IT: Higher PE acceptable (15-35)
        - Banks/Finance: Lower PE expected (8-18)
        - FMCG/Consumer: Premium PE acceptable (25-45)
        - Industrials/Capital Goods: Moderate PE (12-25)
        - Default: Standard PE (10-25)
        
        Returns 0-100 score where:
        - 80-100: Significantly undervalued
        - 60-80: Reasonably valued with upside
        - 40-60: Fairly valued
        - 20-40: Somewhat expensive
        - 0-20: Very expensive
        """
        if not stock.pe_ratio or stock.pe_ratio <= 0:
            return 50  # Neutral when no data
        
        pe = stock.pe_ratio
        sector = (stock.sector or "").lower()
        
        # Sector-adjusted PE thresholds
        if "tech" in sector or "it" in sector or "software" in sector:
            # Tech stocks can trade at higher multiples
            if pe < 12:
                return 90  # Deep value for tech
            elif pe < 18:
                return 80
            elif pe < 25:
                return 65
            elif pe < 35:
                return 50
            elif pe < 50:
                return 35
            else:
                return 20
                
        elif "bank" in sector or "financial" in sector or "nbfc" in sector:
            # Banks typically trade at lower PE
            if pe < 6:
                return 85  # Could be stressed, check NPA
            elif pe < 10:
                return 80
            elif pe < 15:
                return 65
            elif pe < 20:
                return 50
            elif pe < 25:
                return 35
            else:
                return 20
                
        elif "fmcg" in sector or "consumer" in sector:
            # FMCG commands premium valuations
            if pe < 20:
                return 85  # Undervalued for FMCG
            elif pe < 30:
                return 70
            elif pe < 40:
                return 55
            elif pe < 50:
                return 40
            else:
                return 25
                
        elif "pharma" in sector or "healthcare" in sector:
            if pe < 15:
                return 80
            elif pe < 22:
                return 65
            elif pe < 30:
                return 50
            elif pe < 40:
                return 35
            else:
                return 20
                
        else:
            # Default scoring for other sectors
            if pe < 8:
                return 80  # Check for value trap
            elif pe < 12:
                return 75
            elif pe < 18:
                return 65
            elif pe < 25:
                return 50
            elif pe < 35:
                return 35
            else:
                return 20
    
    def _determine_signal(self, score: float) -> Signal:
        """Determine buy/sell signal from overall score."""
        if score >= 75:
            return Signal.STRONG_BUY
        elif score >= 60:
            return Signal.BUY
        elif score >= 40:
            return Signal.HOLD
        elif score >= 25:
            return Signal.SELL
        else:
            return Signal.STRONG_SELL
    
    def _calc_targets(
        self,
        stock: StockSnapshot,
        indicators: TechnicalIndicators,
        signal: Signal,
    ) -> tuple[float, float]:
        """Calculate target price and stop loss."""
        price = stock.price
        atr = indicators.atr or (price * 0.02)
        
        if signal in [Signal.STRONG_BUY, Signal.BUY]:
            # Use resistance as target, support as stop loss
            target = indicators.resistance or (price * 1.10)
            stop_loss = indicators.support or (price - 2 * atr)
        else:
            # For sell signals, reverse targets
            target = indicators.support or (price * 0.90)
            stop_loss = indicators.resistance or (price + 2 * atr)
        
        return round(target, 2), round(stop_loss, 2)
    
    def _determine_risk(
        self,
        stock: StockSnapshot,
        indicators: TechnicalIndicators,
    ) -> RiskLevel:
        """Determine risk level."""
        risk_score = 0
        
        # ATR volatility
        if indicators.atr and stock.price:
            atr_pct = (indicators.atr / stock.price) * 100
            if atr_pct > 4:
                risk_score += 2
            elif atr_pct > 2:
                risk_score += 1
        
        # Small/Micro caps are riskier
        if stock.segment in ["Small Cap", "Micro Cap"]:
            risk_score += 1
        
        # Near 52-week extremes
        if stock.fifty_two_week_high and stock.price:
            pct_from_high = ((stock.fifty_two_week_high - stock.price) / stock.fifty_two_week_high) * 100
            if pct_from_high > 40:
                risk_score += 1
        
        if risk_score >= 3:
            return RiskLevel.HIGH
        elif risk_score >= 1:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_reasons(
        self,
        stock: StockSnapshot,
        indicators: TechnicalIndicators,
        signal: Signal,
        sentiment: Optional[NewsSentiment] = None,
    ) -> list[str]:
        """Generate list of reasons for the recommendation."""
        reasons = []
        
        # NEWS AND SENTIMENT REASONS (Priority - most relevant to user)
        if sentiment:
            # Sentiment-based reasons
            if sentiment.sentiment_label == "POSITIVE":
                reasons.append(f"Positive news sentiment ({sentiment.news_count} news items)")
            elif sentiment.sentiment_label == "NEGATIVE":
                reasons.append(f"Negative news sentiment - caution advised")
            
            # Key events (most important market movers)
            event_descriptions = {
                'acquisition': 'Acquisition/merger news driving momentum',
                'earnings': 'Recent quarterly results impacting price',
                'dividend': 'Dividend/bonus announcement',
                'order': 'New order/contract announced',
                'regulatory': 'Regulatory/policy news affecting stock',
                'management': 'Management change news',
                'fii_dii': 'FII/DII activity reported',
                'rating': 'Analyst rating change',
            }
            for event in sentiment.key_events[:2]:
                if event in event_descriptions:
                    reasons.append(event_descriptions[event])
            
            # Top headline if relevant
            if sentiment.top_headlines and len(reasons) < 3:
                headline = sentiment.top_headlines[0][:60]
                if len(headline) > 50:
                    headline = headline[:50] + "..."
                reasons.append(f"News: {headline}")
        
        # TREND AND MOMENTUM REASONS
        if indicators.trend == Trend.STRONG_UPTREND:
            reasons.append("Strong uptrend confirmed by multiple indicators")
        elif indicators.trend == Trend.UPTREND:
            reasons.append("Stock is in an uptrend")
        elif indicators.trend == Trend.STRONG_DOWNTREND:
            reasons.append("Strong downtrend - avoid")
        elif indicators.trend == Trend.DOWNTREND:
            reasons.append("Stock showing weakness in trend")
        
        # RSI reason
        if indicators.rsi:
            if indicators.rsi < 30:
                reasons.append(f"RSI at {indicators.rsi:.0f} indicates oversold - potential bounce")
            elif indicators.rsi > 70:
                reasons.append(f"RSI at {indicators.rsi:.0f} - overbought, may correct")
        
        # MACD reason
        if indicators.macd_histogram is not None:
            if indicators.macd_histogram > 0:
                reasons.append("MACD bullish crossover")
            else:
                reasons.append("MACD bearish signal")
        
        # Price vs SMA
        if indicators.sma_200 and stock.price:
            if stock.price > indicators.sma_200:
                reasons.append("Trading above 200 SMA (long-term bullish)")
            else:
                reasons.append("Below 200 SMA (long-term bearish)")
        
        # Support/Resistance
        if indicators.support and stock.price:
            support_dist = ((stock.price - indicators.support) / stock.price) * 100
            if support_dist < 5:
                reasons.append(f"Near strong support at ₹{indicators.support:.2f}")
        
        # Valuation
        if stock.pe_ratio:
            if stock.pe_ratio < 15:
                reasons.append(f"Attractive valuation P/E {stock.pe_ratio:.1f}")
            elif stock.pe_ratio > 35:
                reasons.append(f"Expensive valuation P/E {stock.pe_ratio:.1f}")
        
        return reasons[:3]  # Return top 3 reasons
