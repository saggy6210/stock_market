"""
Analysis Module.
Contains AI-powered stock analysis components.
"""

from app.analysis.technical import TechnicalAnalyzer
from app.analysis.recommendation import RecommendationEngine
from app.analysis.screener import MarketScreener
from app.analysis.recovery import RecoveryScreener
from app.analysis.portfolio import PortfolioAnalyzer
from app.analysis.news_sentiment import NewsSentimentAnalyzer
from app.analysis.market_overview import MarketOverviewFetcher, MarketOverview
from app.analysis.news_aggregator import NewsAggregator, MarketNews
from app.analysis.market_intelligence import (
    MarketIntelligenceService,
    MarketIntelligence,
    FIIDIIData,
    StockFIIData,
    FundamentalData,
)
from app.analysis.newsletter import NewsletterGenerator, Newsletter
from app.analysis.portfolio_insights import (
    PortfolioInsightsGenerator,
    PortfolioInsights,
    HoldingAnalysis,
    PortfolioSignal,
    DeclineSummary,
    DetailedBuyRecommendation,
)
from app.analysis.portfolio_email import PortfolioEmailGenerator

__all__ = [
    "TechnicalAnalyzer",
    "RecommendationEngine",
    "MarketScreener",
    "RecoveryScreener",
    "PortfolioAnalyzer",
    "NewsSentimentAnalyzer",
    "MarketOverviewFetcher",
    "MarketOverview",
    "NewsAggregator",
    "MarketNews",
    "MarketIntelligenceService",
    "MarketIntelligence",
    "FIIDIIData",
    "StockFIIData",
    "FundamentalData",
    "NewsletterGenerator",
    "Newsletter",
    "PortfolioInsightsGenerator",
    "PortfolioInsights",
    "HoldingAnalysis",
    "PortfolioSignal",
    "DeclineSummary",
    "DetailedBuyRecommendation",
    "PortfolioEmailGenerator",
]
