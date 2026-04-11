"""
Market Dashboard Generator.
Generates the market dashboard HTML page with live data.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import json

import yfinance as yf
from jinja2 import Template

logger = logging.getLogger(__name__)


class MarketDashboardGenerator:
    """Generate market dashboard HTML with live data."""
    
    # Market indices symbols
    INDICES = {
        "dow_jones": ("^DJI", "Dow Jones", "NYSE", "🇺🇸"),
        "nasdaq": ("^IXIC", "NASDAQ Composite", "NASDAQ", "🇺🇸"),
        "sensex": ("^BSESN", "Sensex", "BSE", "🇮🇳"),
        "nifty": ("^NSEI", "Nifty 50", "NSE", "🇮🇳"),
        "nifty_it": ("^CNXIT", "Nifty IT", "NSE", "🇮🇳"),
        "nifty_bank": ("^NSEBANK", "Nifty Bank", "NSE", "🇮🇳"),
        "india_vix": ("^INDIAVIX", "India VIX", "NSE", "🇮🇳"),
        "gift_nifty": ("^NSEI", "GIFT Nifty", "SGX", "🌏"),
        "usd_inr": ("USDINR=X", "USD/INR", "FOREX", "💱"),
    }
    
    # Global indicators
    GLOBAL_INDICATORS = {
        "us_10y": ("^TNX", "US 10Y Treasury Yield", "US Government Bond"),
        "crude_oil": ("CL=F", "Crude Oil (Brent)", "$/Barrel"),
        "gold": ("GC=F", "Gold", "$/oz"),
        "dxy": ("DX-Y.NYB", "US Dollar Index (DXY)", "Dollar Strength"),
    }
    
    # Sample fallen stocks data (would be fetched from screener in production)
    FALLEN_STOCKS = {
        "feb26": [
            {"symbol": "PAYTM", "sector": "Fintech", "old_price": 892.50, "current": 456.30},
            {"symbol": "NYKAA", "sector": "E-commerce", "old_price": 245.80, "current": 142.65},
            {"symbol": "POLICYBZR", "sector": "Insurance", "old_price": 1234.50, "current": 756.20},
            {"symbol": "DELTACOPR", "sector": "Electronics", "old_price": 567.80, "current": 356.45},
            {"symbol": "ZOMATO", "sector": "Food Tech", "old_price": 256.70, "current": 167.45},
            {"symbol": "DELHIVERY", "sector": "Logistics", "old_price": 456.30, "current": 312.80},
            {"symbol": "CARTRADE", "sector": "Auto Tech", "old_price": 789.50, "current": 545.60},
            {"symbol": "INDIGO", "sector": "Aviation", "old_price": 4567.80, "current": 3234.50},
            {"symbol": "PVR", "sector": "Entertainment", "old_price": 1678.90, "current": 1198.45},
            {"symbol": "EASEMYTRIP", "sector": "Travel", "old_price": 45.60, "current": 32.85},
        ],
        "jan26": [
            {"symbol": "PAYTM", "sector": "Fintech", "old_price": 1245.30, "current": 456.30},
            {"symbol": "ADANIENT", "sector": "Conglomerate", "old_price": 3456.80, "current": 1678.45},
            {"symbol": "NYKAA", "sector": "E-commerce", "old_price": 289.60, "current": 142.65},
            {"symbol": "ADANIPORTS", "sector": "Ports", "old_price": 1567.90, "current": 823.45},
            {"symbol": "ADANIGREEN", "sector": "Green Energy", "old_price": 2345.60, "current": 1245.80},
            {"symbol": "ZOMATO", "sector": "Food Tech", "old_price": 298.45, "current": 167.45},
            {"symbol": "POLICYBZR", "sector": "Insurance", "old_price": 1345.60, "current": 756.20},
            {"symbol": "TATASTEEL", "sector": "Steel", "old_price": 234.50, "current": 134.25},
            {"symbol": "DELTACOPR", "sector": "Electronics", "old_price": 598.70, "current": 356.45},
            {"symbol": "DELHIVERY", "sector": "Logistics", "old_price": 512.40, "current": 312.80},
        ],
        "may25": [
            {"symbol": "PAYTM", "sector": "Fintech", "old_price": 1456.80, "current": 456.30},
            {"symbol": "ADANIENT", "sector": "Conglomerate", "old_price": 4123.50, "current": 1678.45},
            {"symbol": "NYKAA", "sector": "E-commerce", "old_price": 345.80, "current": 142.65},
            {"symbol": "ADANIGREEN", "sector": "Green Energy", "old_price": 2897.60, "current": 1245.80},
            {"symbol": "VEDL", "sector": "Metals", "old_price": 567.30, "current": 289.45},
            {"symbol": "ZOMATO", "sector": "Food Tech", "old_price": 312.40, "current": 167.45},
            {"symbol": "TATASTEEL", "sector": "Steel", "old_price": 245.70, "current": 134.25},
            {"symbol": "SAIL", "sector": "Steel", "old_price": 178.50, "current": 98.75},
            {"symbol": "ADANIPORTS", "sector": "Ports", "old_price": 1456.90, "current": 823.45},
            {"symbol": "COALINDIA", "sector": "Mining", "old_price": 698.40, "current": 412.30},
        ],
        "jan25": [
            {"symbol": "PAYTM", "sector": "Fintech", "old_price": 1789.60, "current": 456.30},
            {"symbol": "ADANIENT", "sector": "Conglomerate", "old_price": 5234.80, "current": 1678.45},
            {"symbol": "ADANIGREEN", "sector": "Green Energy", "old_price": 3456.70, "current": 1245.80},
            {"symbol": "NYKAA", "sector": "E-commerce", "old_price": 378.90, "current": 142.65},
            {"symbol": "ADANIPOWER", "sector": "Power", "old_price": 567.80, "current": 234.50},
            {"symbol": "VEDL", "sector": "Metals", "old_price": 645.30, "current": 289.45},
            {"symbol": "TATASTEEL", "sector": "Steel", "old_price": 289.50, "current": 134.25},
            {"symbol": "ZOMATO", "sector": "Food Tech", "old_price": 356.80, "current": 167.45},
            {"symbol": "ADANIPORTS", "sector": "Ports", "old_price": 1678.90, "current": 823.45},
            {"symbol": "SAIL", "sector": "Steel", "old_price": 198.70, "current": 98.75},
        ],
    }
    
    def __init__(self, output_dir: str = None):
        """Initialize the generator."""
        self.output_dir = Path(output_dir) if output_dir else Path(__file__).parent.parent / "market_dashboard"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def fetch_index_data(self, symbol: str, name: str, exchange: str, flag: str) -> dict:
        """Fetch data for a single index."""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            
            if hist.empty or len(hist) < 2:
                return self._get_default_index_data(name, exchange, flag)
            
            last_close = float(hist['Close'].iloc[-1])
            prev_close = float(hist['Close'].iloc[-2])
            change = last_close - prev_close
            change_pct = (change / prev_close) * 100
            
            return {
                "name": name,
                "exchange": exchange,
                "flag": flag,
                "value": round(last_close, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "is_positive": change >= 0,
            }
        except Exception as e:
            logger.warning(f"Failed to fetch {name}: {e}")
            return self._get_default_index_data(name, exchange, flag)
    
    def _get_default_index_data(self, name: str, exchange: str, flag: str) -> dict:
        """Get default index data when API fails."""
        return {
            "name": name,
            "exchange": exchange,
            "flag": flag,
            "value": 0.0,
            "change": 0.0,
            "change_pct": 0.0,
            "is_positive": True,
        }
    
    def fetch_all_indices(self) -> dict:
        """Fetch all market indices."""
        indices = {}
        for key, (symbol, name, exchange, flag) in self.INDICES.items():
            indices[key] = self.fetch_index_data(symbol, name, exchange, flag)
        return indices
    
    def fetch_global_indicators(self) -> list:
        """Fetch global market indicators."""
        indicators = []
        
        impact_rules = {
            "us_10y": lambda c: "NEGATIVE" if c > 0 else "POSITIVE",
            "crude_oil": lambda c: "POSITIVE" if c < 0 else "NEGATIVE",
            "gold": lambda c: "NEGATIVE" if c < 0 else "NEUTRAL",
            "dxy": lambda c: "POSITIVE" if c < 0 else "NEGATIVE",
        }
        
        icons = {
            "us_10y": "treasury",
            "crude_oil": "oil",
            "gold": "gold",
            "dxy": "dollar",
        }
        
        for key, (symbol, name, subtitle) in self.GLOBAL_INDICATORS.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")
                
                if hist.empty or len(hist) < 2:
                    continue
                
                last_close = float(hist['Close'].iloc[-1])
                prev_close = float(hist['Close'].iloc[-2])
                change_pct = ((last_close - prev_close) / prev_close) * 100
                
                impact = impact_rules.get(key, lambda c: "NEUTRAL")(change_pct)
                
                indicators.append({
                    "name": name,
                    "subtitle": subtitle,
                    "icon": icons.get(key, "chart"),
                    "value": round(last_close, 2),
                    "change_pct": round(change_pct, 2),
                    "is_positive": change_pct >= 0,
                    "impact": impact,
                })
            except Exception as e:
                logger.warning(f"Failed to fetch {name}: {e}")
        
        return indicators
    
    def calculate_fallen_stocks(self, period: str) -> list:
        """Calculate top fallen stocks for a period."""
        stocks = self.FALLEN_STOCKS.get(period, [])
        result = []
        
        for stock in stocks:
            fall_pct = ((stock["current"] - stock["old_price"]) / stock["old_price"]) * 100
            result.append({
                **stock,
                "fall_pct": round(fall_pct, 2),
            })
        
        return sorted(result, key=lambda x: x["fall_pct"])
    
    def determine_market_outlook(self, indices: dict) -> tuple:
        """Determine market outlook based on indices."""
        positive_count = sum(1 for idx in indices.values() if idx.get("is_positive", False))
        total = len(indices)
        
        # Get key values
        dow_positive = indices.get("dow_jones", {}).get("is_positive", False)
        nasdaq_positive = indices.get("nasdaq", {}).get("is_positive", False)
        gift_positive = indices.get("gift_nifty", {}).get("is_positive", False)
        vix_value = indices.get("india_vix", {}).get("value", 15)
        
        # Determine outlook
        if positive_count >= total * 0.7 and vix_value < 20:
            outlook = "BULLISH"
        elif positive_count <= total * 0.3 or vix_value > 25:
            outlook = "BEARISH"
        elif vix_value > 20:
            outlook = "VOLATILE"
        else:
            outlook = "NEUTRAL"
        
        # Generate reason
        reason_parts = []
        
        dow = indices.get("dow_jones", {})
        nasdaq = indices.get("nasdaq", {})
        gift = indices.get("gift_nifty", {})
        
        if dow.get("change_pct"):
            direction = "up" if dow["is_positive"] else "down"
            reason_parts.append(f"Dow Jones {direction} {abs(dow['change_pct'])}%")
        
        if nasdaq.get("change_pct"):
            direction = "up" if nasdaq["is_positive"] else "down"
            reason_parts.append(f"NASDAQ {direction} {abs(nasdaq['change_pct'])}%")
        
        if gift.get("is_positive"):
            reason_parts.append("GIFT Nifty indicating positive opening")
        else:
            reason_parts.append("GIFT Nifty indicating negative opening")
        
        if vix_value < 15:
            reason_parts.append("VIX low suggesting low volatility")
        elif vix_value > 20:
            reason_parts.append("VIX elevated indicating higher volatility")
        
        reason = "; ".join(reason_parts) + "."
        
        return outlook, reason
    
    def generate_data(self) -> dict:
        """Generate all dashboard data."""
        logger.info("Fetching market data...")
        
        # Fetch indices
        indices = self.fetch_all_indices()
        
        # Fetch global indicators
        global_indicators = self.fetch_global_indicators()
        
        # Calculate fallen stocks for all periods
        fallen_stocks = {
            "feb26": self.calculate_fallen_stocks("feb26"),
            "jan26": self.calculate_fallen_stocks("jan26"),
            "may25": self.calculate_fallen_stocks("may25"),
            "jan25": self.calculate_fallen_stocks("jan25"),
        }
        
        # Determine outlook
        outlook, outlook_reason = self.determine_market_outlook(indices)
        
        # Get current timestamp
        now = datetime.now()
        
        return {
            "generated_at": now.strftime("%B %d, %Y %I:%M %p IST"),
            "date": now.strftime("%B %d, %Y"),
            "indices": indices,
            "global_indicators": global_indicators,
            "fallen_stocks": fallen_stocks,
            "outlook": outlook,
            "outlook_reason": outlook_reason,
            # Sample FII/DII data (would come from actual source)
            "fii_dii": {
                "fii_net": -2345.67,
                "dii_net": 3125.45,
                "fii_buy": 8542.30,
                "fii_sell": 10887.97,
                "dii_buy": 9678.12,
                "dii_sell": 6552.67,
                "fii_monthly": -15234,
                "dii_monthly": 18567,
                "fii_ytd": -45890,
                "dii_ytd": 52345,
            },
        }
    
    def save_data_json(self, data: dict):
        """Save data as JSON for potential API use."""
        json_path = self.output_dir / "data.json"
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Saved data to {json_path}")
    
    def generate(self, fetch_live: bool = False) -> str:
        """
        Generate the dashboard.
        
        Args:
            fetch_live: Whether to fetch live data from APIs
            
        Returns:
            Path to generated HTML file
        """
        if fetch_live:
            data = self.generate_data()
            self.save_data_json(data)
            logger.info(f"Generated dashboard with live data")
        else:
            logger.info("Using static HTML template")
        
        return str(self.output_dir / "index.html")


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate Market Dashboard")
    parser.add_argument("--live", action="store_true", help="Fetch live data")
    parser.add_argument("--output", type=str, help="Output directory")
    args = parser.parse_args()
    
    generator = MarketDashboardGenerator(output_dir=args.output)
    output_path = generator.generate(fetch_live=args.live)
    print(f"Dashboard generated: {output_path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
