# Stock Market Screener & Newsletter

Automated stock market analysis with daily recommendations, market intelligence, and comprehensive newsletter for NSE/BSE stocks.

## Features

### Core Analysis
- **Daily Market Scan** - Analyzes 700+ stocks daily at 7 AM IST
- **Technical Analysis** - RSI, MACD, SMA (20/50/200), Bollinger Bands, ADX
- **Fundamental Analysis** - P/E, P/B, ROE, EPS, Market Cap, Debt/Equity
- **News Sentiment** - Real-time news analysis for market-moving events
- **Recovery Screener** - Identifies stocks bouncing from 52-week lows

### Newsletter & Intelligence
- **Market Newsletter** - Comprehensive daily market intelligence report
- **Top Stories** - Aggregated from MoneyControl, Economic Times, Mint
- **Earnings & Results** - Quarterly results and profit announcements
- **Order Bookings** - Contract wins, new orders, deal announcements
- **Regulatory News** - SEBI, RBI, government policy updates
- **Insider Trading** - Bulk deals, promoter transactions
- **Macro Indicators** - Crude oil, gold, US treasury, FII/DII data
- **5 Stock Predictions** - AI-powered stock movement forecasts based on news

### Data Sources
| Source | Data Type |
|--------|-----------|
| MoneyControl | Market news, FII/DII |
| Economic Times | Stock news, earnings |
| BSE/NSE | Corporate announcements |
| Yahoo Finance | Fundamentals, technicals |
| Screener.in | Ratios, balance sheet |

## Quick Start

```bash
cd stock_market
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your SMTP settings

# Run the API server
python run.py
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | API info |
| `GET /health` | Health check |
| `POST /run` | Run daily scan with newsletter |
| `GET /buy-signals` | Top buy recommendations |
| `GET /sell-signals` | Top sell recommendations |
| `POST /analyze-portfolio` | Analyze uploaded CSV |
| `GET /report` | Get last generated report |

## Email Report Sections

1. **Global Market Overview** - US markets, GIFT Nifty, Currency
2. **Market Outlook** - Bullish/Bearish prediction with reasons
3. **Market Newsletter**
   - Macro indicators (VIX, FII/DII, Crude, Gold)
   - Top 5 stock movement predictions
   - Top market stories
   - Earnings & quarterly results
   - Order bookings & contracts
   - Regulatory updates
   - Insider trading news
4. **Top 10 Buy Recommendations** - With 3 reasons each
5. **Top 10 Sell Recommendations** - With 3 reasons each
6. **Recovery Candidates** - Stocks bouncing from lows

## Environment Variables

```env
# Email (required)
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_TO=recipient@example.com

# Scheduler (7 AM IST daily)
SCHEDULE_HOUR=7
SCHEDULE_MINUTE=0
```

## Architecture

```
app/
├── analysis/
│   ├── technical.py          # RSI, MACD, SMA, Bollinger
│   ├── recommendation.py     # Buy/Sell signal generation
│   ├── news_sentiment.py     # News sentiment analysis
│   ├── news_aggregator.py    # Multi-source news fetching
│   ├── market_intelligence.py # Fundamentals, macro data
│   ├── newsletter.py         # Newsletter generation
│   ├── market_overview.py    # Global indices
│   ├── screener.py           # Market screening
│   └── recovery.py           # Recovery stock finder
├── services/
│   └── stock_service.py      # Main orchestration
├── notification/
│   └── emailer.py            # SMTP email sender
└── scheduler/
    └── jobs.py               # APScheduler config
```

## Docker

```bash
docker-compose up -d
```

## License

MIT