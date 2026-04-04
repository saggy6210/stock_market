"""
Market Screener.
Screens all stocks for buy and sell signals.
"""

import logging
from typing import Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.data.models import StockSnapshot, StockRecommendation, Signal
from app.data.nse_client import NSEClient
from app.analysis.technical import TechnicalAnalyzer
from app.analysis.recommendation import RecommendationEngine

logger = logging.getLogger(__name__)


class MarketScreener:
    """Screen market for buy/sell opportunities."""
    
    def __init__(self, max_workers: int = 10):
        """
        Initialize the market screener.
        
        Args:
            max_workers: Max parallel workers for analysis
        """
        self._nse_client = NSEClient()
        self._technical = TechnicalAnalyzer()
        self._recommendation = RecommendationEngine()
        self._max_workers = max_workers
    
    def screen(
        self,
        stocks: list[StockSnapshot] = None,
        top_n: int = 10,
    ) -> Tuple[list[StockRecommendation], list[StockRecommendation]]:
        """
        Screen all stocks for buy and sell signals.
        
        Args:
            stocks: List of stocks to screen (fetches all if not provided)
            top_n: Number of top buy/sell signals to return
            
        Returns:
            Tuple of (buy_signals, sell_signals)
        """
        if stocks is None:
            logger.info("Fetching all stocks from NSE...")
            stocks = self._nse_client.fetch_all_stocks(include_micro=True)
        
        logger.info(f"Screening {len(stocks)} stocks...")
        
        recommendations = []
        
        # Analyze stocks in parallel
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {
                executor.submit(self._analyze_stock, stock): stock
                for stock in stocks
            }
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        recommendations.append(result)
                except Exception as e:
                    stock = futures[future]
                    logger.debug(f"Failed to analyze {stock.symbol}: {e}")
        
        logger.info(f"Analyzed {len(recommendations)} stocks successfully")
        
        # Separate buy and sell signals
        buy_signals = [
            r for r in recommendations
            if r.signal in [Signal.STRONG_BUY, Signal.BUY]
        ]
        sell_signals = [
            r for r in recommendations
            if r.signal in [Signal.STRONG_SELL, Signal.SELL]
        ]
        
        # Sort by score
        buy_signals.sort(key=lambda x: x.overall_score, reverse=True)
        sell_signals.sort(key=lambda x: x.overall_score)  # Lowest scores first
        
        return buy_signals[:top_n], sell_signals[:top_n]
    
    def _analyze_stock(self, stock: StockSnapshot) -> StockRecommendation:
        """Analyze a single stock."""
        # Fetch historical data
        df = self._nse_client.fetch_stock_history(stock.symbol, period="6mo")
        
        if df is None or df.empty or len(df) < 20:
            return None
        
        # Update stock with latest price from history
        stock.price = float(df["Close"].iloc[-1])
        
        # Calculate indicators
        indicators = self._technical.analyze(df)
        
        # Get average volume
        avg_volume = float(df["Volume"].mean()) if "Volume" in df.columns else None
        
        # Generate recommendation
        return self._recommendation.analyze(stock, indicators, avg_volume)
