"""
Portfolio Analyzer.
Analyzes user's portfolio from CSV file.
"""

import logging
from pathlib import Path
from typing import Optional
import pandas as pd

from app.data.models import PortfolioHolding, StockRecommendation
from app.data.nse_client import NSEClient
from app.analysis.technical import TechnicalAnalyzer
from app.analysis.recommendation import RecommendationEngine

logger = logging.getLogger(__name__)


class PortfolioAnalyzer:
    """Analyze portfolio holdings from CSV."""
    
    def __init__(self):
        """Initialize the portfolio analyzer."""
        self._nse_client = NSEClient()
        self._technical = TechnicalAnalyzer()
        self._recommendation = RecommendationEngine()
    
    def analyze_csv(self, csv_path: str) -> list[PortfolioHolding]:
        """
        Analyze portfolio from CSV file.
        
        Expected CSV columns:
        - Symbol or Instrument (stock symbol)
        - Quantity or Qty
        - Avg_Cost or Average (purchase average)
        - LTP or Current_Price (optional, will fetch if not present)
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            list: List of PortfolioHolding with recommendations
        """
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            logger.error(f"Failed to read CSV: {e}")
            return []
        
        # Normalize column names
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
        
        # Map common column names
        symbol_col = self._find_column(df, ["symbol", "instrument", "stock", "scrip"])
        qty_col = self._find_column(df, ["quantity", "qty", "shares"])
        avg_col = self._find_column(df, ["avg_cost", "average", "avg", "buy_price", "purchase_price"])
        ltp_col = self._find_column(df, ["ltp", "current_price", "price", "cmp"])
        
        if not symbol_col or not qty_col:
            logger.error("CSV must have Symbol and Quantity columns")
            return []
        
        holdings = []
        
        for _, row in df.iterrows():
            symbol = str(row[symbol_col]).strip().upper()
            
            # Clean symbol (remove exchange suffixes)
            symbol = symbol.replace(".NS", "").replace(".BO", "").replace("-EQ", "")
            
            quantity = int(row[qty_col]) if pd.notna(row[qty_col]) else 0
            avg_cost = float(row[avg_col]) if avg_col and pd.notna(row.get(avg_col)) else 0
            
            # Get current price
            if ltp_col and pd.notna(row.get(ltp_col)):
                current_price = float(row[ltp_col])
            else:
                current_price = self._fetch_current_price(symbol)
            
            # Calculate P&L
            investment = quantity * avg_cost
            current_value = quantity * current_price
            pnl = current_value - investment
            pnl_pct = (pnl / investment * 100) if investment > 0 else 0
            
            # Get recommendation
            recommendation = self._get_recommendation(symbol)
            
            holdings.append(PortfolioHolding(
                symbol=symbol,
                quantity=quantity,
                avg_cost=avg_cost,
                current_price=current_price,
                investment=round(investment, 2),
                current_value=round(current_value, 2),
                pnl=round(pnl, 2),
                pnl_pct=round(pnl_pct, 2),
                recommendation=recommendation,
            ))
        
        return holdings
    
    def _find_column(self, df: pd.DataFrame, names: list[str]) -> Optional[str]:
        """Find column by possible names."""
        for name in names:
            if name in df.columns:
                return name
        return None
    
    def _fetch_current_price(self, symbol: str) -> float:
        """Fetch current price for a symbol."""
        info = self._nse_client.fetch_stock_info(symbol)
        if info:
            return info.get("regularMarketPrice", 0) or info.get("currentPrice", 0)
        return 0
    
    def _get_recommendation(self, symbol: str) -> Optional[StockRecommendation]:
        """Get recommendation for a stock."""
        try:
            # Fetch historical data
            df = self._nse_client.fetch_stock_history(symbol, period="6mo")
            if df is None or df.empty:
                return None
            
            # Get stock info
            info = self._nse_client.fetch_stock_info(symbol)
            
            from app.data.models import StockSnapshot
            
            stock = StockSnapshot(
                symbol=symbol,
                company_name=info.get("shortName", symbol) if info else symbol,
                sector=info.get("sector", "") if info else "",
                price=float(df["Close"].iloc[-1]),
                pe_ratio=info.get("trailingPE") if info else None,
            )
            
            # Calculate indicators
            indicators = self._technical.analyze(df)
            
            # Get average volume
            avg_volume = float(df["Volume"].mean()) if "Volume" in df.columns else None
            
            # Generate recommendation
            return self._recommendation.analyze(stock, indicators, avg_volume)
            
        except Exception as e:
            logger.warning(f"Failed to get recommendation for {symbol}: {e}")
            return None
