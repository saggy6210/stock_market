"""
News Aggregator Module.
Fetches market news from multiple sources for newsletter generation.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """Single news item."""
    headline: str
    source: str
    url: str
    published: Optional[datetime] = None
    summary: str = ""
    category: str = "general"  # earnings, orders, regulatory, insider, macro
    sentiment: str = "neutral"  # positive, negative, neutral
    stocks_mentioned: list = field(default_factory=list)
    impact_score: float = 0.0  # 0-100, higher = more impactful


@dataclass
class MarketNews:
    """Collection of market news."""
    top_stories: list[NewsItem] = field(default_factory=list)
    earnings_news: list[NewsItem] = field(default_factory=list)
    order_booking_news: list[NewsItem] = field(default_factory=list)
    regulatory_news: list[NewsItem] = field(default_factory=list)
    insider_trading: list[NewsItem] = field(default_factory=list)
    macro_news: list[NewsItem] = field(default_factory=list)
    stock_movements: list[dict] = field(default_factory=list)  # Top 5 movers with reasons


class NewsAggregator:
    """
    Aggregates news from multiple Indian financial news sources.
    
    Sources:
    - MoneyControl
    - Economic Times Markets
    - Mint (LiveMint)
    - Pulse by Zerodha
    - Groww
    - BSE/NSE Announcements
    - Yahoo Finance
    """
    
    # News source configurations
    SOURCES = {
        "moneycontrol": {
            "base_url": "https://www.moneycontrol.com",
            "news_url": "https://www.moneycontrol.com/news/business/markets/",
            "earnings_url": "https://www.moneycontrol.com/news/business/earnings/",
        },
        "economictimes": {
            "base_url": "https://economictimes.indiatimes.com",
            "markets_url": "https://economictimes.indiatimes.com/markets",
        },
        "mint": {
            "base_url": "https://www.livemint.com",
            "markets_url": "https://www.livemint.com/market/stock-market-news",
        },
        "pulse_zerodha": {
            "base_url": "https://pulse.zerodha.com",
            "news_url": "https://pulse.zerodha.com/",
        },
        "groww": {
            "base_url": "https://groww.in",
            "news_url": "https://groww.in/blog/category/market-news",
        },
        "bse": {
            "announcements_url": "https://www.bseindia.com/corporates/ann.html",
        },
        "nse": {
            "announcements_url": "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
        },
    }
    
    # Keywords for categorization
    CATEGORY_KEYWORDS = {
        "earnings": ["quarterly", "results", "profit", "loss", "revenue", "earnings", "q1", "q2", "q3", "q4", 
                     "net profit", "ebitda", "margin", "beats estimate", "misses estimate", "yoy", "qoq"],
        "orders": ["order", "contract", "deal", "wins", "bags", "secures", "awarded", "booking", 
                   "receives order", "new order", "order book", "order inflow"],
        "regulatory": ["sebi", "rbi", "government", "policy", "regulation", "tax", "gst", "budget",
                       "ministry", "cabinet", "approval", "ban", "investigation", "penalty", "fine"],
        "insider": ["promoter", "stake", "shareholding", "bulk deal", "block deal", "insider",
                    "bought", "sold", "acquisition", "merger", "takeover", "buyback"],
        "macro": ["inflation", "gdp", "interest rate", "repo rate", "crude oil", "dollar", "rupee",
                  "fii", "dii", "foreign", "global", "us fed", "economy", "unemployment"],
    }
    
    # Sentiment keywords
    POSITIVE_KEYWORDS = ["surge", "jump", "rise", "gain", "profit", "growth", "beats", "strong", 
                         "record", "high", "upgrade", "bullish", "positive", "boom", "rally",
                         "soar", "breakthrough", "expansion", "wins", "secures", "bags"]
    NEGATIVE_KEYWORDS = ["fall", "drop", "decline", "loss", "crash", "down", "weak", "miss",
                         "downgrade", "bearish", "negative", "crisis", "concern", "warning",
                         "slump", "plunge", "cut", "reduces", "penalty", "investigation", "scam"]
    
    def __init__(self):
        """Initialize the news aggregator."""
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    def fetch_all_news(self) -> MarketNews:
        """
        Fetch news from all sources and categorize.
        
        Returns:
            MarketNews: Categorized market news
        """
        news = MarketNews()
        
        # Fetch from different sources
        mc_news = self._fetch_moneycontrol_news()
        et_news = self._fetch_et_news()
        mint_news = self._fetch_mint_news()
        pulse_news = self._fetch_pulse_zerodha_news()
        groww_news = self._fetch_groww_news()
        
        # Combine and categorize
        all_news = mc_news + et_news + mint_news + pulse_news + groww_news
        
        for item in all_news:
            self._categorize_news(item)
            self._analyze_sentiment(item)
            
            # Sort into categories
            if item.category == "earnings":
                news.earnings_news.append(item)
            elif item.category == "orders":
                news.order_booking_news.append(item)
            elif item.category == "regulatory":
                news.regulatory_news.append(item)
            elif item.category == "insider":
                news.insider_trading.append(item)
            elif item.category == "macro":
                news.macro_news.append(item)
            else:
                news.top_stories.append(item)
        
        # Sort by impact score
        news.top_stories = sorted(news.top_stories, key=lambda x: x.impact_score, reverse=True)[:10]
        news.earnings_news = sorted(news.earnings_news, key=lambda x: x.impact_score, reverse=True)[:5]
        news.order_booking_news = sorted(news.order_booking_news, key=lambda x: x.impact_score, reverse=True)[:5]
        
        # Generate stock movement predictions
        news.stock_movements = self._predict_stock_movements(all_news)
        
        return news
    
    def _fetch_moneycontrol_news(self) -> list[NewsItem]:
        """Fetch news from MoneyControl."""
        news_items = []
        
        try:
            # Fetch market news
            response = self._session.get(
                self.SOURCES["moneycontrol"]["news_url"],
                timeout=10
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Parse news articles
                articles = soup.select(".news_list li, .FL.mob_line") or soup.select("li.clearfix")
                
                for article in articles[:20]:
                    try:
                        link = article.select_one("a")
                        if not link:
                            continue
                        
                        headline = link.get_text(strip=True)
                        url = link.get("href", "")
                        
                        if headline and len(headline) > 20:
                            news_items.append(NewsItem(
                                headline=headline,
                                source="MoneyControl",
                                url=url if url.startswith("http") else f"https://www.moneycontrol.com{url}",
                                category="general",
                            ))
                    except Exception:
                        continue
                        
        except Exception as e:
            logger.warning(f"Error fetching MoneyControl news: {e}")
        
        return news_items
    
    def _fetch_et_news(self) -> list[NewsItem]:
        """Fetch news from Economic Times."""
        news_items = []
        
        try:
            response = self._session.get(
                f"{self.SOURCES['economictimes']['markets_url']}/stocks/news",
                timeout=10
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Parse news articles
                articles = soup.select(".eachStory, .story-box, article")
                
                for article in articles[:20]:
                    try:
                        link = article.select_one("a")
                        if not link:
                            continue
                        
                        headline = link.get_text(strip=True)
                        url = link.get("href", "")
                        
                        if headline and len(headline) > 20:
                            news_items.append(NewsItem(
                                headline=headline,
                                source="Economic Times",
                                url=url if url.startswith("http") else f"https://economictimes.indiatimes.com{url}",
                                category="general",
                            ))
                    except Exception:
                        continue
                        
        except Exception as e:
            logger.warning(f"Error fetching ET news: {e}")
        
        return news_items
    
    def _fetch_mint_news(self) -> list[NewsItem]:
        """Fetch news from LiveMint."""
        news_items = []
        
        try:
            response = self._session.get(
                self.SOURCES["mint"]["markets_url"],
                timeout=10
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Parse news articles
                articles = soup.select(".headline, .listingNew a, article a")
                
                for article in articles[:15]:
                    try:
                        headline = article.get_text(strip=True)
                        url = article.get("href", "")
                        
                        if headline and len(headline) > 20:
                            news_items.append(NewsItem(
                                headline=headline,
                                source="Mint",
                                url=url if url.startswith("http") else f"https://www.livemint.com{url}",
                                category="general",
                            ))
                    except Exception:
                        continue
                        
        except Exception as e:
            logger.warning(f"Error fetching Mint news: {e}")
        
        return news_items
    
    def _fetch_pulse_zerodha_news(self) -> list[NewsItem]:
        """Fetch news from Pulse by Zerodha."""
        news_items = []
        
        try:
            response = self._session.get(
                self.SOURCES["pulse_zerodha"]["news_url"],
                timeout=10
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Parse news articles
                articles = soup.select(".post-title a, .entry-title a, article a")
                
                for article in articles[:15]:
                    try:
                        headline = article.get_text(strip=True)
                        url = article.get("href", "")
                        
                        if headline and len(headline) > 20:
                            news_items.append(NewsItem(
                                headline=headline,
                                source="Pulse (Zerodha)",
                                url=url if url.startswith("http") else f"https://pulse.zerodha.com{url}",
                                category="general",
                            ))
                    except Exception:
                        continue
                        
        except Exception as e:
            logger.warning(f"Error fetching Pulse news: {e}")
        
        return news_items
    
    def _fetch_groww_news(self) -> list[NewsItem]:
        """Fetch news from Groww."""
        news_items = []
        
        try:
            response = self._session.get(
                self.SOURCES["groww"]["news_url"],
                timeout=10
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Parse news articles
                articles = soup.select(".post-card a, .blog-card a, article a")
                
                for article in articles[:10]:
                    try:
                        headline = article.get_text(strip=True)
                        url = article.get("href", "")
                        
                        if headline and len(headline) > 20:
                            news_items.append(NewsItem(
                                headline=headline,
                                source="Groww",
                                url=url if url.startswith("http") else f"https://groww.in{url}",
                                category="general",
                            ))
                    except Exception:
                        continue
                        
        except Exception as e:
            logger.warning(f"Error fetching Groww news: {e}")
        
        return news_items
    
    def _categorize_news(self, item: NewsItem) -> None:
        """Categorize a news item based on keywords."""
        headline_lower = item.headline.lower()
        
        max_matches = 0
        best_category = "general"
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in headline_lower)
            if matches > max_matches:
                max_matches = matches
                best_category = category
        
        item.category = best_category
        
        # Extract stock symbols mentioned
        item.stocks_mentioned = self._extract_stocks(item.headline)
    
    def _analyze_sentiment(self, item: NewsItem) -> None:
        """Analyze sentiment of a news item."""
        headline_lower = item.headline.lower()
        
        positive_count = sum(1 for kw in self.POSITIVE_KEYWORDS if kw in headline_lower)
        negative_count = sum(1 for kw in self.NEGATIVE_KEYWORDS if kw in headline_lower)
        
        if positive_count > negative_count:
            item.sentiment = "positive"
            item.impact_score = min(50 + positive_count * 10, 100)
        elif negative_count > positive_count:
            item.sentiment = "negative"
            item.impact_score = min(50 + negative_count * 10, 100)
        else:
            item.sentiment = "neutral"
            item.impact_score = 30
        
        # Boost impact for important categories
        if item.category in ["earnings", "orders", "regulatory"]:
            item.impact_score = min(item.impact_score + 20, 100)
    
    def _extract_stocks(self, text: str) -> list[str]:
        """Extract potential stock symbols from text."""
        # Common Indian stock names
        stock_patterns = [
            r'\b(RELIANCE|TCS|INFY|HDFC|ICICI|WIPRO|ITC|BAJAJ|TATA|ADANI|'
            r'MARUTI|SUNPHARMA|TITAN|NTPC|ONGC|SBI|BHARTI|KOTAK|AXIS|LT|'
            r'HINDALCO|TATASTEEL|JSWSTEEL|VEDANTA|COAL|POWERGRID|TECHM|'
            r'HCLTECH|ULTRACEMCO|GRASIM|NESTLEIND|HINDUNILVR|ASIANPAINT)\b'
        ]
        
        matches = []
        for pattern in stock_patterns:
            found = re.findall(pattern, text.upper())
            matches.extend(found)
        
        return list(set(matches))
    
    def _predict_stock_movements(self, all_news: list[NewsItem]) -> list[dict]:
        """
        Predict top 5 stock movements based on news.
        
        Returns:
            List of predictions with stock, direction, and reason
        """
        stock_news = {}
        
        # Aggregate news by stock
        for item in all_news:
            for stock in item.stocks_mentioned:
                if stock not in stock_news:
                    stock_news[stock] = {"positive": 0, "negative": 0, "neutral": 0, "news": []}
                
                stock_news[stock][item.sentiment] += 1
                stock_news[stock]["news"].append(item)
        
        # Calculate movement predictions
        predictions = []
        for stock, data in stock_news.items():
            sentiment_score = data["positive"] - data["negative"]
            
            if abs(sentiment_score) > 0:
                direction = "UP" if sentiment_score > 0 else "DOWN"
                confidence = min(abs(sentiment_score) * 20 + 40, 95)
                
                # Get most impactful news as reason
                top_news = sorted(data["news"], key=lambda x: x.impact_score, reverse=True)
                reason = top_news[0].headline if top_news else "Multiple news factors"
                
                predictions.append({
                    "stock": stock,
                    "direction": direction,
                    "confidence": confidence,
                    "reason": reason[:100],
                    "news_count": len(data["news"]),
                    "sentiment_score": sentiment_score,
                })
        
        # Sort by confidence and return top 5
        predictions = sorted(predictions, key=lambda x: x["confidence"], reverse=True)
        return predictions[:5]
    
    def fetch_corporate_announcements(self) -> list[NewsItem]:
        """
        Fetch corporate announcements from BSE.
        Includes order bookings, quarterly results, board meetings.
        """
        announcements = []
        
        try:
            # BSE corporate announcements API
            response = self._session.get(
                "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w",
                params={"strCat": "Corp. Action", "strType": "C"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                for item in data.get("Table", [])[:10]:
                    announcements.append(NewsItem(
                        headline=item.get("NEWSSUB", ""),
                        source="BSE",
                        url=f"https://www.bseindia.com/corporates/anndet.aspx?newsid={item.get('NEWSID', '')}",
                        category="regulatory",
                    ))
        except Exception as e:
            logger.warning(f"Error fetching BSE announcements: {e}")
        
        return announcements
