"""
News and Sentiment Analyzer.
Fetches news and analyzes sentiment for stocks.
"""

import logging
import re
from typing import Optional
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
import yfinance as yf

logger = logging.getLogger(__name__)


@dataclass
class NewsSentiment:
    """News sentiment analysis result."""
    symbol: str
    sentiment_score: float  # -1 to 1
    sentiment_label: str  # POSITIVE, NEGATIVE, NEUTRAL
    news_count: int
    top_headlines: list[str]
    key_events: list[str]  # Acquisitions, earnings, etc.


class NewsSentimentAnalyzer:
    """Analyze news sentiment for stocks."""
    
    # Positive keywords indicating bullish sentiment
    POSITIVE_KEYWORDS = [
        'surge', 'rally', 'gain', 'profit', 'growth', 'bullish', 'buy', 'upgrade',
        'outperform', 'beat', 'strong', 'record', 'high', 'boom', 'soar', 'jump',
        'positive', 'optimistic', 'breakthrough', 'success', 'expansion', 'recovery',
        'dividend', 'buyback', 'acquisition', 'partnership', 'deal', 'revenue',
        'order', 'contract', 'approval', 'launch', 'innovation', 'milestone',
        'quarterly profit', 'revenue growth', 'market share', 'new product',
        'fii buying', 'dii buying', 'institutional buying', 'stake increase',
    ]
    
    # Negative keywords indicating bearish sentiment
    NEGATIVE_KEYWORDS = [
        'fall', 'drop', 'loss', 'decline', 'bearish', 'sell', 'downgrade',
        'underperform', 'miss', 'weak', 'low', 'crash', 'plunge', 'slump',
        'negative', 'pessimistic', 'warning', 'failure', 'layoff', 'fraud',
        'debt', 'lawsuit', 'investigation', 'scandal', 'default', 'bankruptcy',
        'postpone', 'delay', 'scam', 'probe', 'sebi', 'ed raid', 'cbi',
        'downgrade', 'target cut', 'stake sale', 'promoter selling',
        'fii selling', 'dii selling', 'institutional selling', 'exit',
        'privatization delay', 'regulatory issue', 'compliance', 'penalty',
    ]
    
    # Event keywords for specific market-moving events
    EVENT_KEYWORDS = {
        'acquisition': ['acquisition', 'acquire', 'takeover', 'merger', 'buyout'],
        'earnings': ['quarterly', 'earnings', 'profit', 'revenue', 'results', 'q1', 'q2', 'q3', 'q4'],
        'dividend': ['dividend', 'payout', 'bonus'],
        'order': ['order', 'contract', 'deal', 'agreement'],
        'regulatory': ['sebi', 'rbi', 'government', 'policy', 'regulation', 'approval'],
        'management': ['ceo', 'cfo', 'promoter', 'director', 'resignation', 'appointment'],
        'fii_dii': ['fii', 'dii', 'institutional', 'stake', 'shareholding'],
        'rating': ['upgrade', 'downgrade', 'target', 'rating', 'recommendation'],
    }
    
    def __init__(self):
        """Initialize the news sentiment analyzer."""
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
    
    def get_stock_sentiment(self, symbol: str) -> NewsSentiment:
        """
        Get comprehensive sentiment analysis for a stock.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            NewsSentiment: Sentiment analysis result
        """
        news_items = []
        
        # Fetch from Yahoo Finance
        yf_news = self._fetch_yahoo_news(symbol)
        news_items.extend(yf_news)
        
        # Fetch from Google News
        google_news = self._fetch_google_news(symbol)
        news_items.extend(google_news)
        
        if not news_items:
            return NewsSentiment(
                symbol=symbol,
                sentiment_score=0.0,
                sentiment_label="NEUTRAL",
                news_count=0,
                top_headlines=[],
                key_events=[],
            )
        
        # Analyze sentiment
        total_score = 0.0
        headlines = []
        events = []
        
        for news in news_items[:15]:  # Analyze top 15 news
            title = news.get('title', '')
            headlines.append(title)
            
            # Calculate sentiment
            score, _ = self._analyze_sentiment(title)
            total_score += score
            
            # Detect key events
            detected_events = self._detect_events(title)
            events.extend(detected_events)
        
        # Average sentiment
        avg_score = total_score / len(news_items) if news_items else 0
        
        # Determine label
        if avg_score > 0.15:
            label = "POSITIVE"
        elif avg_score < -0.15:
            label = "NEGATIVE"
        else:
            label = "NEUTRAL"
        
        return NewsSentiment(
            symbol=symbol,
            sentiment_score=round(avg_score, 3),
            sentiment_label=label,
            news_count=len(news_items),
            top_headlines=headlines[:5],
            key_events=list(set(events))[:3],
        )
    
    def _fetch_yahoo_news(self, symbol: str) -> list[dict]:
        """Fetch news from Yahoo Finance."""
        news_items = []
        try:
            for suffix in [".NS", ".BO"]:
                ticker = yf.Ticker(f"{symbol}{suffix}")
                yf_news = ticker.news
                if yf_news:
                    for item in yf_news[:10]:
                        news_items.append({
                            'title': item.get('title', ''),
                            'publisher': item.get('publisher', ''),
                            'source': 'yahoo',
                        })
                    break
        except Exception as e:
            logger.debug(f"Failed to fetch Yahoo news for {symbol}: {e}")
        
        return news_items
    
    def _fetch_google_news(self, symbol: str) -> list[dict]:
        """Fetch news from Google News."""
        news_items = []
        try:
            query = f"{symbol} stock NSE"
            url = f"https://news.google.com/search?q={query}+when:7d&hl=en-IN&gl=IN&ceid=IN:en"
            
            response = self._session.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                articles = soup.find_all('article')[:10]
                
                for article in articles:
                    # Try to find headline
                    headline_elem = article.find(['h3', 'h4', 'a'])
                    if headline_elem:
                        title = headline_elem.get_text(strip=True)
                        if title and len(title) > 10:
                            news_items.append({
                                'title': title,
                                'source': 'google',
                            })
        except Exception as e:
            logger.debug(f"Failed to fetch Google news for {symbol}: {e}")
        
        return news_items
    
    def _analyze_sentiment(self, text: str) -> tuple[float, str]:
        """
        Analyze sentiment of text.
        
        Returns:
            tuple: (score from -1 to 1, label)
        """
        text_lower = text.lower()
        
        positive_count = sum(1 for kw in self.POSITIVE_KEYWORDS if kw in text_lower)
        negative_count = sum(1 for kw in self.NEGATIVE_KEYWORDS if kw in text_lower)
        
        total = positive_count + negative_count
        if total == 0:
            return 0.0, "NEUTRAL"
        
        score = (positive_count - negative_count) / total
        
        if score > 0.2:
            label = "POSITIVE"
        elif score < -0.2:
            label = "NEGATIVE"
        else:
            label = "NEUTRAL"
        
        return score, label
    
    def _detect_events(self, text: str) -> list[str]:
        """Detect key events from text."""
        text_lower = text.lower()
        events = []
        
        for event_type, keywords in self.EVENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    events.append(event_type)
                    break
        
        return events
    
    def get_market_news_summary(self) -> dict:
        """Get overall market news summary."""
        market_indices = ['NIFTY', 'SENSEX', 'BANKNIFTY']
        all_news = []
        
        for index in market_indices:
            news = self._fetch_google_news(index)
            all_news.extend(news)
        
        # Analyze overall sentiment
        positive = 0
        negative = 0
        
        for news in all_news:
            score, _ = self._analyze_sentiment(news.get('title', ''))
            if score > 0.1:
                positive += 1
            elif score < -0.1:
                negative += 1
        
        total = positive + negative
        if total == 0:
            mood = "NEUTRAL"
        elif positive > negative * 1.5:
            mood = "BULLISH"
        elif negative > positive * 1.5:
            mood = "BEARISH"
        else:
            mood = "MIXED"
        
        return {
            "mood": mood,
            "positive_news": positive,
            "negative_news": negative,
            "total_news": len(all_news),
        }
