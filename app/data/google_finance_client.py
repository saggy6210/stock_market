"""
Google Finance Client.
Fetches stock data from Google Finance for Indian stocks (NSE/BSE).
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Request timeout in seconds
REQUEST_TIMEOUT = 10


@dataclass
class GoogleFinanceData:
    """Stock data from Google Finance."""
    symbol: str
    company_name: str = ""
    current_price: float = 0.0
    previous_close: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    day_high: float = 0.0
    day_low: float = 0.0
    year_high: float = 0.0
    year_low: float = 0.0
    market_cap: str = ""
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    sector: str = "Unknown"


class GoogleFinanceClient:
    """Client to fetch stock data from Google Finance."""
    
    BASE_URL = "https://www.google.com/finance/quote"
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    def __init__(self):
        """Initialize the Google Finance client."""
        self._session = requests.Session()
        self._session.headers.update(self.HEADERS)
    
    def get_stock_data(self, symbol: str, exchange: str = "NSE") -> Optional[GoogleFinanceData]:
        """
        Fetch stock data from Google Finance.
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE', 'HDFCBANK')
            exchange: Exchange code ('NSE' or 'BSE')
            
        Returns:
            GoogleFinanceData if successful, None otherwise
        """
        try:
            # Clean symbol
            clean_symbol = symbol.upper().strip()
            
            # Try NSE first, then BSE
            exchanges_to_try = [exchange, "BSE"] if exchange == "NSE" else [exchange, "NSE"]
            
            for exch in exchanges_to_try:
                url = f"{self.BASE_URL}/{clean_symbol}:{exch}"
                
                try:
                    response = self._session.get(url, timeout=REQUEST_TIMEOUT)
                    
                    if response.status_code == 200:
                        data = self._parse_google_finance_page(response.text, clean_symbol)
                        if data and data.current_price > 0:
                            logger.debug(f"Got data for {symbol} from Google Finance ({exch})")
                            return data
                except Exception as e:
                    logger.debug(f"Failed to fetch {symbol} from {exch}: {e}")
                    continue
            
            logger.warning(f"Could not fetch {symbol} from Google Finance")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching {symbol} from Google Finance: {e}")
            return None
    
    def _parse_google_finance_page(self, html: str, symbol: str) -> Optional[GoogleFinanceData]:
        """Parse Google Finance page HTML."""
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            data = GoogleFinanceData(symbol=symbol)
            
            # Get company name from title
            title_tag = soup.find("title")
            if title_tag:
                title_text = title_tag.get_text()
                # Title format: "RELIANCE Stock Price - Reliance Industries Ltd"
                if " Stock Price" in title_text:
                    data.company_name = title_text.split(" Stock Price")[0].strip()
            
            # Get current price - look for the main price element
            price_element = soup.find("div", {"data-last-price": True})
            if price_element:
                data.current_price = float(price_element.get("data-last-price", 0))
            else:
                # Alternative: look for price in YMlKec class
                price_div = soup.find("div", class_="YMlKec")
                if price_div:
                    price_text = price_div.get_text().replace("₹", "").replace(",", "").strip()
                    try:
                        data.current_price = float(price_text)
                    except ValueError:
                        pass
            
            # Get change and change percentage
            change_elements = soup.find_all("div", class_="JwB6zf")
            for elem in change_elements:
                text = elem.get_text().strip()
                if "%" in text:
                    # Parse change percentage
                    try:
                        pct_match = re.search(r"([+-]?\d+\.?\d*)%", text)
                        if pct_match:
                            data.change_pct = float(pct_match.group(1))
                    except ValueError:
                        pass
                elif "₹" in text or text.replace("-", "").replace(".", "").replace(",", "").isdigit():
                    # Parse absolute change
                    try:
                        change_text = text.replace("₹", "").replace(",", "").replace("+", "").strip()
                        data.change = float(change_text)
                    except ValueError:
                        pass
            
            # Extract additional info from data tables
            info_rows = soup.find_all("div", class_="P6K39c")
            for row in info_rows:
                try:
                    label_elem = row.find("div", class_="mfs7Fc")
                    value_elem = row.find("div", class_="P6K39c")
                    
                    if not label_elem or not value_elem:
                        continue
                    
                    label = label_elem.get_text().strip().lower()
                    value = value_elem.get_text().strip()
                    
                    if "previous close" in label:
                        data.previous_close = self._parse_number(value)
                    elif "day range" in label:
                        parts = value.split("-")
                        if len(parts) == 2:
                            data.day_low = self._parse_number(parts[0])
                            data.day_high = self._parse_number(parts[1])
                    elif "year range" in label or "52-week" in label:
                        parts = value.split("-")
                        if len(parts) == 2:
                            data.year_low = self._parse_number(parts[0])
                            data.year_high = self._parse_number(parts[1])
                    elif "market cap" in label:
                        data.market_cap = value
                    elif "p/e ratio" in label:
                        data.pe_ratio = self._parse_number(value)
                    elif "dividend yield" in label:
                        data.dividend_yield = self._parse_number(value.replace("%", ""))
                        
                except Exception:
                    continue
            
            # Calculate previous close from current price and change if not found
            if data.previous_close == 0 and data.current_price > 0 and data.change != 0:
                data.previous_close = data.current_price - data.change
            
            return data
            
        except Exception as e:
            logger.debug(f"Error parsing Google Finance page: {e}")
            return None
    
    def _parse_number(self, text: str) -> float:
        """Parse a number from text, handling Indian number format."""
        try:
            # Remove currency symbols and commas
            clean = text.replace("₹", "").replace(",", "").replace(" ", "").strip()
            
            # Handle suffixes like T, B, Cr, L
            multiplier = 1
            if clean.endswith("T"):
                multiplier = 1e12
                clean = clean[:-1]
            elif clean.endswith("B"):
                multiplier = 1e9
                clean = clean[:-1]
            elif clean.endswith("Cr"):
                multiplier = 1e7
                clean = clean[:-2]
            elif clean.endswith("L"):
                multiplier = 1e5
                clean = clean[:-1]
            
            return float(clean) * multiplier
        except (ValueError, AttributeError):
            return 0.0
    
    def get_multiple_stocks(self, symbols: list[str], exchange: str = "NSE") -> dict[str, GoogleFinanceData]:
        """
        Fetch data for multiple stocks.
        
        Args:
            symbols: List of stock symbols
            exchange: Default exchange code
            
        Returns:
            Dictionary mapping symbols to their data
        """
        results = {}
        for symbol in symbols:
            data = self.get_stock_data(symbol, exchange)
            if data:
                results[symbol] = data
        return results


# Singleton instance
_client: Optional[GoogleFinanceClient] = None


def get_google_finance_client() -> GoogleFinanceClient:
    """Get the singleton Google Finance client instance."""
    global _client
    if _client is None:
        _client = GoogleFinanceClient()
    return _client
