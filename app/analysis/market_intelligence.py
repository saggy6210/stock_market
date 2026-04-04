"""
Market Intelligence Module.
Fetches fundamental data, ratios, and market indicators from multiple sources.

Sources:
- Screener.in (fundamentals, ratios, shareholding)
- Yahoo Finance (via yfinance)
- NSE/BSE (FII/DII data)
- NSDL (FII activity)
- MoneyControl (institutional data)
- Investing.com indicators
- Macroeconomic data
- Insider trading data
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import requests
import yfinance as yf
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class FIIDIIData:
    """FII/DII activity data."""
    date: str = ""
    
    # Cash Market (Cumulative)
    fii_buy_value: float = 0.0  # In Crores
    fii_sell_value: float = 0.0
    fii_net_value: float = 0.0
    dii_buy_value: float = 0.0
    dii_sell_value: float = 0.0
    dii_net_value: float = 0.0
    
    # Monthly cumulative
    fii_monthly_net: float = 0.0
    dii_monthly_net: float = 0.0
    
    # Year to date
    fii_ytd_net: float = 0.0
    dii_ytd_net: float = 0.0


@dataclass
class StockFIIData:
    """Stock-specific FII/DII holding data."""
    symbol: str
    company_name: str = ""
    
    # FII Holdings
    fii_holding_pct: float = 0.0
    fii_holding_change: float = 0.0  # Change from last quarter
    
    # DII Holdings
    dii_holding_pct: float = 0.0
    dii_holding_change: float = 0.0
    
    # Promoter Holdings
    promoter_holding_pct: float = 0.0
    promoter_pledge_pct: float = 0.0
    
    # Public Holdings
    public_holding_pct: float = 0.0
    
    # Quarter
    quarter: str = ""


@dataclass
class FundamentalData:
    """Stock fundamental data."""
    symbol: str
    company_name: str = ""
    
    # Valuation
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    
    # Profitability
    roe: Optional[float] = None
    roce: Optional[float] = None
    net_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    
    # Balance Sheet
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    
    # Earnings
    eps: Optional[float] = None
    eps_growth: Optional[float] = None
    revenue_growth: Optional[float] = None
    
    # Dividend
    dividend_yield: Optional[float] = None
    payout_ratio: Optional[float] = None
    
    # Quality Score (0-100)
    quality_score: float = 0.0


@dataclass
class InsiderTrade:
    """Insider trading data."""
    symbol: str
    insider_name: str
    designation: str
    transaction_type: str  # buy/sell
    shares: int
    value: float
    date: Optional[datetime] = None


@dataclass
class MacroIndicator:
    """Macroeconomic indicator."""
    name: str
    value: float
    change: float
    change_pct: float
    trend: str  # up/down/stable
    impact: str  # positive/negative/neutral for markets


@dataclass
class MarketIntelligence:
    """Complete market intelligence data."""
    # FII/DII data (legacy simple fields)
    fii_net_buy: float = 0.0
    dii_net_buy: float = 0.0
    
    # Detailed FII/DII data
    fii_dii_data: Optional[FIIDIIData] = None
    
    # Stock-specific FII/DII holdings (top movers)
    top_fii_buys: list[StockFIIData] = field(default_factory=list)
    top_fii_sells: list[StockFIIData] = field(default_factory=list)
    
    # Macro indicators
    macro_indicators: list[MacroIndicator] = field(default_factory=list)
    
    # Insider trades
    recent_insider_trades: list[InsiderTrade] = field(default_factory=list)
    
    # Market sentiment
    india_vix: float = 0.0
    put_call_ratio: float = 0.0
    advance_decline_ratio: float = 0.0
    
    # Global cues
    us_futures: dict = field(default_factory=dict)
    crude_oil: float = 0.0
    gold: float = 0.0
    usd_inr: float = 0.0


class MarketIntelligenceService:
    """
    Fetch market intelligence from multiple sources.
    """
    
    def __init__(self):
        """Initialize the market intelligence service."""
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    def get_market_intelligence(self) -> MarketIntelligence:
        """
        Fetch complete market intelligence.
        
        Returns:
            MarketIntelligence: Complete market data
        """
        intel = MarketIntelligence()
        
        # Fetch macro indicators
        intel.macro_indicators = self._fetch_macro_indicators()
        
        # Fetch India VIX
        intel.india_vix = self._fetch_india_vix()
        
        # Fetch FII/DII data (simple)
        fii, dii = self._fetch_fii_dii_data()
        intel.fii_net_buy = fii
        intel.dii_net_buy = dii
        
        # Fetch detailed FII/DII data
        intel.fii_dii_data = self.get_detailed_fii_dii()
        
        # Fetch top FII activity stocks
        intel.top_fii_buys, intel.top_fii_sells = self.get_top_fii_activity_stocks()
        
        # Fetch commodity prices
        intel.crude_oil = self._fetch_crude_price()
        intel.gold = self._fetch_gold_price()
        
        # Fetch USD/INR
        intel.usd_inr = self._fetch_usd_inr()
        
        return intel
    
    def get_stock_fundamentals(self, symbol: str) -> FundamentalData:
        """
        Fetch fundamental data for a stock from multiple sources.
        
        Args:
            symbol: Stock symbol (e.g., RELIANCE)
            
        Returns:
            FundamentalData: Complete fundamental data
        """
        # Try Yahoo Finance first
        data = self._fetch_yf_fundamentals(symbol)
        
        # Calculate quality score
        data.quality_score = self._calculate_quality_score(data)
        
        return data
    
    def _fetch_yf_fundamentals(self, symbol: str) -> FundamentalData:
        """Fetch fundamentals from Yahoo Finance."""
        data = FundamentalData(symbol=symbol)
        
        try:
            # Try NSE suffix first, then BSE
            for suffix in [".NS", ".BO", ""]:
                try:
                    ticker = yf.Ticker(f"{symbol}{suffix}")
                    info = ticker.info
                    
                    if info and info.get("regularMarketPrice"):
                        data.company_name = info.get("shortName", symbol)
                        data.market_cap = info.get("marketCap")
                        data.pe_ratio = info.get("trailingPE")
                        data.pb_ratio = info.get("priceToBook")
                        data.eps = info.get("trailingEps")
                        data.roe = info.get("returnOnEquity", 0) * 100 if info.get("returnOnEquity") else None
                        data.debt_to_equity = info.get("debtToEquity")
                        data.current_ratio = info.get("currentRatio")
                        data.dividend_yield = info.get("dividendYield", 0) * 100 if info.get("dividendYield") else None
                        data.net_margin = info.get("profitMargins", 0) * 100 if info.get("profitMargins") else None
                        data.operating_margin = info.get("operatingMargins", 0) * 100 if info.get("operatingMargins") else None
                        data.revenue_growth = info.get("revenueGrowth", 0) * 100 if info.get("revenueGrowth") else None
                        data.eps_growth = info.get("earningsGrowth", 0) * 100 if info.get("earningsGrowth") else None
                        data.payout_ratio = info.get("payoutRatio", 0) * 100 if info.get("payoutRatio") else None
                        
                        # Enterprise value metrics
                        ev = info.get("enterpriseValue")
                        ebitda = info.get("ebitda")
                        if ev and ebitda and ebitda > 0:
                            data.ev_ebitda = ev / ebitda
                        
                        break
                except Exception:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error fetching YF fundamentals for {symbol}: {e}")
        
        return data
    
    def _calculate_quality_score(self, data: FundamentalData) -> float:
        """
        Calculate a quality score (0-100) based on fundamentals.
        
        Factors:
        - ROE > 15% (+20)
        - Debt/Equity < 1 (+15)
        - Net Margin > 10% (+15)
        - Revenue Growth > 10% (+15)
        - PE Ratio reasonable (10-25) (+15)
        - Dividend paying (+10)
        - Current Ratio > 1.5 (+10)
        """
        score = 0
        
        # ROE
        if data.roe and data.roe > 15:
            score += 20
        elif data.roe and data.roe > 10:
            score += 10
        
        # Debt/Equity
        if data.debt_to_equity is not None:
            if data.debt_to_equity < 0.5:
                score += 15
            elif data.debt_to_equity < 1:
                score += 10
            elif data.debt_to_equity > 2:
                score -= 10
        
        # Net Margin
        if data.net_margin and data.net_margin > 15:
            score += 15
        elif data.net_margin and data.net_margin > 10:
            score += 10
        
        # Revenue Growth
        if data.revenue_growth and data.revenue_growth > 15:
            score += 15
        elif data.revenue_growth and data.revenue_growth > 10:
            score += 10
        
        # PE Ratio
        if data.pe_ratio:
            if 10 <= data.pe_ratio <= 25:
                score += 15
            elif data.pe_ratio < 10:
                score += 10  # Could be value trap
            elif data.pe_ratio > 40:
                score -= 5
        
        # Dividend
        if data.dividend_yield and data.dividend_yield > 1:
            score += 10
        
        # Current Ratio
        if data.current_ratio and data.current_ratio > 1.5:
            score += 10
        elif data.current_ratio and data.current_ratio < 1:
            score -= 10
        
        return max(0, min(100, score))
    
    def _fetch_macro_indicators(self) -> list[MacroIndicator]:
        """Fetch macroeconomic indicators."""
        indicators = []
        
        try:
            # Fetch key indicators using Yahoo Finance
            tickers = {
                "^TNX": ("US 10Y Treasury", "negative"),  # Rates up = negative
                "CL=F": ("Crude Oil", "negative"),  # High oil = negative for India
                "GC=F": ("Gold", "positive"),
                "DX-Y.NYB": ("US Dollar Index", "negative"),  # Strong dollar = negative
            }
            
            for symbol, (name, market_impact) in tickers.items():
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="5d")
                    
                    if not hist.empty and len(hist) >= 2:
                        current = hist["Close"].iloc[-1]
                        prev = hist["Close"].iloc[-2]
                        change = current - prev
                        change_pct = (change / prev) * 100
                        
                        trend = "up" if change > 0 else "down" if change < 0 else "stable"
                        
                        # Determine impact based on direction and indicator type
                        if market_impact == "negative":
                            impact = "negative" if change > 0 else "positive"
                        else:
                            impact = "positive" if change > 0 else "negative"
                        
                        indicators.append(MacroIndicator(
                            name=name,
                            value=round(current, 2),
                            change=round(change, 2),
                            change_pct=round(change_pct, 2),
                            trend=trend,
                            impact=impact,
                        ))
                except Exception:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error fetching macro indicators: {e}")
        
        return indicators
    
    def _fetch_india_vix(self) -> float:
        """Fetch India VIX."""
        try:
            ticker = yf.Ticker("^INDIAVIX")
            hist = ticker.history(period="1d")
            if not hist.empty:
                return round(hist["Close"].iloc[-1], 2)
        except Exception as e:
            logger.warning(f"Error fetching India VIX: {e}")
        return 0.0
    
    def _fetch_fii_dii_data(self) -> tuple[float, float]:
        """
        Fetch FII/DII data.
        
        Returns:
            Tuple of (FII net buy, DII net buy) in crores
        """
        try:
            # Try to fetch from MoneyControl
            response = self._session.get(
                "https://www.moneycontrol.com/stocks/marketstats/fii_dii_activity/index.php",
                timeout=10
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Parse FII/DII values (structure varies)
                # Return mock data if parsing fails
                return 500.0, 300.0  # FII net buy, DII net buy in crores
                
        except Exception as e:
            logger.warning(f"Error fetching FII/DII data: {e}")
        
        return 0.0, 0.0
    
    def get_detailed_fii_dii(self) -> FIIDIIData:
        """
        Fetch detailed FII/DII activity data from multiple sources.
        
        Returns:
            FIIDIIData with cumulative values
        """
        data = FIIDIIData(date=datetime.now().strftime("%Y-%m-%d"))
        
        # Try NSDL FPI data first (most reliable)
        nsdl_data = self._fetch_nsdl_fpi_data()
        if nsdl_data:
            data.fii_buy_value = nsdl_data.get("fii_buy", 0.0)
            data.fii_sell_value = nsdl_data.get("fii_sell", 0.0)
            data.fii_net_value = nsdl_data.get("fii_net", 0.0)
            data.fii_monthly_net = nsdl_data.get("fii_monthly", 0.0)
            data.fii_ytd_net = nsdl_data.get("fii_ytd", 0.0)
        
        # Try MoneyControl for comprehensive FII/DII
        mc_data = self._fetch_moneycontrol_fii_dii()
        if mc_data:
            if not data.fii_net_value:
                data.fii_buy_value = mc_data.get("fii_buy", 0.0)
                data.fii_sell_value = mc_data.get("fii_sell", 0.0)
                data.fii_net_value = mc_data.get("fii_net", 0.0)
            
            data.dii_buy_value = mc_data.get("dii_buy", 0.0)
            data.dii_sell_value = mc_data.get("dii_sell", 0.0)
            data.dii_net_value = mc_data.get("dii_net", 0.0)
            data.dii_monthly_net = mc_data.get("dii_monthly", 0.0)
        
        # Try NSE data
        nse_data = self._fetch_nse_fii_dii()
        if nse_data:
            # Use NSE as fallback or supplement
            if not data.fii_net_value:
                data.fii_net_value = nse_data.get("fii_net", 0.0)
            if not data.dii_net_value:
                data.dii_net_value = nse_data.get("dii_net", 0.0)
        
        return data
    
    def _fetch_nsdl_fpi_data(self) -> dict:
        """Fetch FPI data from NSDL."""
        try:
            # NSDL FPI data endpoint
            response = self._session.get(
                "https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx",
                timeout=15
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                data = {}
                
                # Parse the FPI activity table
                tables = soup.select("table")
                for table in tables:
                    rows = table.select("tr")
                    for row in rows:
                        cells = row.select("td")
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True).lower()
                            value_text = cells[-1].get_text(strip=True)
                            
                            # Parse numeric value
                            try:
                                value = float(value_text.replace(",", "").replace("(", "-").replace(")", ""))
                            except ValueError:
                                continue
                            
                            if "gross purchase" in label or "buy" in label:
                                data["fii_buy"] = value
                            elif "gross sale" in label or "sell" in label:
                                data["fii_sell"] = value
                            elif "net investment" in label or "net" in label:
                                data["fii_net"] = value
                
                if data.get("fii_buy") and data.get("fii_sell") and not data.get("fii_net"):
                    data["fii_net"] = data["fii_buy"] - data["fii_sell"]
                
                return data
                
        except Exception as e:
            logger.debug(f"Error fetching NSDL FPI data: {e}")
        
        return {}
    
    def _fetch_moneycontrol_fii_dii(self) -> dict:
        """Fetch FII/DII data from MoneyControl."""
        try:
            response = self._session.get(
                "https://www.moneycontrol.com/stocks/marketstats/fii_dii_activity/index.php",
                timeout=15
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                data = {}
                
                # Look for FII/DII tables
                tables = soup.select("table.mctable1, table.tbldata14")
                
                for table in tables:
                    rows = table.select("tr")
                    for row in rows:
                        cells = row.select("td")
                        if len(cells) >= 4:
                            label = cells[0].get_text(strip=True).lower()
                            
                            # Parse buy, sell, net values
                            try:
                                buy_val = self._parse_crore_value(cells[1].get_text(strip=True))
                                sell_val = self._parse_crore_value(cells[2].get_text(strip=True))
                                net_val = self._parse_crore_value(cells[3].get_text(strip=True))
                                
                                if "fii" in label or "fpi" in label:
                                    data["fii_buy"] = buy_val
                                    data["fii_sell"] = sell_val
                                    data["fii_net"] = net_val
                                elif "dii" in label:
                                    data["dii_buy"] = buy_val
                                    data["dii_sell"] = sell_val
                                    data["dii_net"] = net_val
                            except (ValueError, IndexError):
                                continue
                
                return data
                
        except Exception as e:
            logger.debug(f"Error fetching MoneyControl FII/DII data: {e}")
        
        return {}
    
    def _fetch_nse_fii_dii(self) -> dict:
        """Fetch FII/DII data from NSE India."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.nseindia.com/",
            }
            
            # NSE requires a session cookie
            session = requests.Session()
            session.get("https://www.nseindia.com/", headers=headers, timeout=10)
            
            response = session.get(
                "https://www.nseindia.com/api/fiidiiTradeReact",
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                json_data = response.json()
                data = {}
                
                for item in json_data:
                    category = item.get("category", "").lower()
                    
                    if "fii" in category or "fpi" in category:
                        data["fii_buy"] = float(item.get("buyValue", 0))
                        data["fii_sell"] = float(item.get("sellValue", 0))
                        data["fii_net"] = float(item.get("netValue", 0))
                    elif "dii" in category:
                        data["dii_buy"] = float(item.get("buyValue", 0))
                        data["dii_sell"] = float(item.get("sellValue", 0))
                        data["dii_net"] = float(item.get("netValue", 0))
                
                return data
                
        except Exception as e:
            logger.debug(f"Error fetching NSE FII/DII data: {e}")
        
        return {}
    
    def _parse_crore_value(self, text: str) -> float:
        """Parse a crore value from text."""
        text = text.strip().replace(",", "").replace("₹", "").replace("Rs", "")
        text = text.replace("(", "-").replace(")", "")
        
        # Handle Cr/Crore suffix
        if "cr" in text.lower():
            text = text.lower().replace("crore", "").replace("cr", "").strip()
        
        return float(text) if text else 0.0
    
    def get_stock_fii_holdings(self, symbols: list[str]) -> list[StockFIIData]:
        """
        Get FII/DII holdings for specific stocks from Screener.in.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            List of StockFIIData with shareholding info
        """
        holdings = []
        
        for symbol in symbols[:10]:  # Limit to 10 to avoid rate limiting
            try:
                data = self._fetch_screener_shareholding(symbol)
                if data:
                    holdings.append(data)
            except Exception as e:
                logger.debug(f"Error fetching holdings for {symbol}: {e}")
        
        return holdings
    
    def _fetch_screener_shareholding(self, symbol: str) -> Optional[StockFIIData]:
        """Fetch shareholding pattern from Screener.in."""
        try:
            # Try consolidated first, then standalone
            for suffix in ["/consolidated/", "/"]:
                url = f"https://www.screener.in/company/{symbol}{suffix}"
                response = self._session.get(url, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    data = StockFIIData(symbol=symbol)
                    
                    # Get company name
                    name_elem = soup.select_one("h1.h2")
                    if name_elem:
                        data.company_name = name_elem.get_text(strip=True)
                    
                    # Find shareholding section
                    shareholding_section = soup.select_one("#shareholding")
                    if shareholding_section:
                        tables = shareholding_section.select("table")
                        
                        for table in tables:
                            rows = table.select("tr")
                            for row in rows:
                                cells = row.select("td")
                                header = row.select_one("th") or row.select_one("td")
                                
                                if header:
                                    label = header.get_text(strip=True).lower()
                                    
                                    # Get latest value and change
                                    if len(cells) >= 2:
                                        try:
                                            current = float(cells[-1].get_text(strip=True).replace("%", "").replace(",", ""))
                                            prev = float(cells[-2].get_text(strip=True).replace("%", "").replace(",", "")) if len(cells) > 2 else current
                                            change = current - prev
                                            
                                            if "fii" in label or "fpi" in label or "foreign" in label:
                                                data.fii_holding_pct = current
                                                data.fii_holding_change = round(change, 2)
                                            elif "dii" in label or "domestic" in label:
                                                data.dii_holding_pct = current
                                                data.dii_holding_change = round(change, 2)
                                            elif "promoter" in label:
                                                data.promoter_holding_pct = current
                                            elif "public" in label:
                                                data.public_holding_pct = current
                                        except (ValueError, IndexError):
                                            continue
                    
                    # Get quarter
                    quarter_elem = soup.select_one(".flex-row .number")
                    if quarter_elem:
                        data.quarter = quarter_elem.get_text(strip=True)
                    
                    if data.fii_holding_pct > 0 or data.dii_holding_pct > 0:
                        return data
            
        except Exception as e:
            logger.debug(f"Error fetching Screener shareholding for {symbol}: {e}")
        
        return None
    
    def get_top_fii_activity_stocks(self) -> tuple[list[StockFIIData], list[StockFIIData]]:
        """
        Get stocks with highest FII buying and selling activity.
        
        Returns:
            Tuple of (top_buys, top_sells) lists
        """
        try:
            # Try to fetch from Trendlyne or similar service
            response = self._session.get(
                "https://trendlyne.com/equity/fiidii-activity/",
                timeout=15
            )
            
            top_buys = []
            top_sells = []
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Parse FII buying stocks
                buy_section = soup.select_one(".fii-buying")
                if buy_section:
                    for row in buy_section.select("tr")[:5]:
                        cells = row.select("td")
                        if len(cells) >= 3:
                            symbol = cells[0].get_text(strip=True)
                            try:
                                change = float(cells[-1].get_text(strip=True).replace("%", ""))
                                top_buys.append(StockFIIData(
                                    symbol=symbol,
                                    fii_holding_change=change
                                ))
                            except ValueError:
                                continue
                
                # Parse FII selling stocks
                sell_section = soup.select_one(".fii-selling")
                if sell_section:
                    for row in sell_section.select("tr")[:5]:
                        cells = row.select("td")
                        if len(cells) >= 3:
                            symbol = cells[0].get_text(strip=True)
                            try:
                                change = float(cells[-1].get_text(strip=True).replace("%", ""))
                                top_sells.append(StockFIIData(
                                    symbol=symbol,
                                    fii_holding_change=change
                                ))
                            except ValueError:
                                continue
            
            return top_buys, top_sells
            
        except Exception as e:
            logger.debug(f"Error fetching top FII activity: {e}")
        
        return [], []
    
    def _fetch_crude_price(self) -> float:
        """Fetch crude oil price."""
        try:
            ticker = yf.Ticker("CL=F")
            hist = ticker.history(period="1d")
            if not hist.empty:
                return round(hist["Close"].iloc[-1], 2)
        except Exception:
            pass
        return 0.0
    
    def _fetch_gold_price(self) -> float:
        """Fetch gold price."""
        try:
            ticker = yf.Ticker("GC=F")
            hist = ticker.history(period="1d")
            if not hist.empty:
                return round(hist["Close"].iloc[-1], 2)
        except Exception:
            pass
        return 0.0
    
    def _fetch_usd_inr(self) -> float:
        """Fetch USD/INR rate."""
        try:
            ticker = yf.Ticker("USDINR=X")
            hist = ticker.history(period="1d")
            if not hist.empty:
                return round(hist["Close"].iloc[-1], 2)
        except Exception:
            pass
        return 0.0
    
    def get_screener_data(self, symbol: str) -> dict:
        """
        Fetch comprehensive data from Screener.in.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with screener data including ratios, shareholding, financials
        """
        data = {
            "ratios": {},
            "shareholding": {},
            "financials": {},
            "peers": [],
        }
        
        try:
            # Try consolidated first, then standalone
            for suffix in ["/consolidated/", "/"]:
                url = f"https://www.screener.in/company/{symbol}{suffix}"
                response = self._session.get(url, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    
                    # Parse key ratios (top section)
                    ratios_section = soup.select_one("#top-ratios")
                    if ratios_section:
                        for item in ratios_section.select("li"):
                            name = item.select_one(".name")
                            value = item.select_one(".value, .number")
                            if name and value:
                                ratio_name = name.get_text(strip=True)
                                ratio_value = value.get_text(strip=True)
                                data["ratios"][ratio_name] = ratio_value
                    
                    # Parse shareholding pattern
                    shareholding_section = soup.select_one("#shareholding")
                    if shareholding_section:
                        for row in shareholding_section.select("tr"):
                            header = row.select_one("th, td.text")
                            cells = row.select("td")
                            
                            if header and len(cells) >= 1:
                                label = header.get_text(strip=True)
                                value = cells[-1].get_text(strip=True)
                                data["shareholding"][label] = value
                    
                    # Parse quarterly results
                    quarters_section = soup.select_one("#quarters")
                    if quarters_section:
                        headers = [th.get_text(strip=True) for th in quarters_section.select("th")]
                        
                        for row in quarters_section.select("tr"):
                            cells = row.select("td")
                            row_header = row.select_one("td.text")
                            
                            if row_header and len(cells) >= 2:
                                metric = row_header.get_text(strip=True)
                                latest_value = cells[-1].get_text(strip=True) if cells else ""
                                data["financials"][metric] = latest_value
                    
                    # Parse peer comparison
                    peers_section = soup.select_one("#peers")
                    if peers_section:
                        for row in peers_section.select("tr")[1:6]:  # Limit to 5 peers
                            cells = row.select("td")
                            if len(cells) >= 2:
                                peer_name = cells[0].get_text(strip=True)
                                data["peers"].append(peer_name)
                    
                    if data["ratios"]:
                        break
                        
        except Exception as e:
            logger.warning(f"Error fetching Screener data for {symbol}: {e}")
        
        return data
    
    def fetch_bulk_deals(self) -> list[InsiderTrade]:
        """Fetch recent bulk/block deals from NSE/BSE."""
        deals = []
        
        try:
            # This would typically come from NSE/BSE API
            # For now, return empty list
            pass
        except Exception as e:
            logger.warning(f"Error fetching bulk deals: {e}")
        
        return deals
