# Stock Market Screener - Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           STOCK MARKET SCREENER                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────┐    ┌───────────────┐    ┌───────────────┐               │
│  │   Scheduler   │    │    FastAPI    │    │   Dashboard   │               │
│  │  (APScheduler)│    │   REST API    │    │ (GitHub Pages)│               │
│  │               │    │               │    │               │               │
│  │ Daily 6:55 AM │    │ /run, /buy,   │    │  index.html   │               │
│  │     IST       │    │ /sell, etc.   │    │               │               │
│  └───────┬───────┘    └───────┬───────┘    └───────────────┘               │
│          │                    │                                             │
│          └────────────┬───────┘                                             │
│                       ▼                                                     │
│          ┌─────────────────────────────┐                                   │
│          │       Stock Service         │                                   │
│          │   (Main Orchestrator)       │                                   │
│          └─────────────┬───────────────┘                                   │
│                        │                                                    │
│    ┌───────────────────┼───────────────────┐                               │
│    ▼                   ▼                   ▼                               │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│ │   Market    │  │   News      │  │  Technical  │                         │
│ │  Screener   │  │ Aggregator  │  │  Analysis   │                         │
│ └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                         │
│        │                │                │                                 │
│        └────────────────┼────────────────┘                                 │
│                         ▼                                                  │
│          ┌─────────────────────────────┐                                   │
│          │     Email Notification      │                                   │
│          │     (HTML Newsletter)       │                                   │
│          └─────────────────────────────┘                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Daily Analysis Pipeline

```
1. Dashboard Generation
   └── run_pipeline() → Generates market_dashboard/data/dashboard_data.json

2. Market Scan
   ├── NSE Client → Fetches 700+ stocks from NIFTY 100, MIDCAP 100, SMALLCAP 100
   ├── Technical Analysis → RSI, MACD, SMA, Bollinger, ADX
   ├── Market Screener → Generates buy/sell signals
   └── Recovery Screener → Identifies stocks bouncing from lows

3. News Aggregation
   ├── MoneyControl → Market news, FII/DII
   ├── Economic Times → Stock news, earnings
   ├── Mint (LiveMint) → Market analysis
   ├── Pulse Zerodha → Trading insights
   └── Groww → Market news

4. Newsletter Generation
   ├── Market Overview → Global indices, FII/DII, VIX
   ├── Top Stories → Most impactful news
   ├── Earnings & Results → Quarterly updates
   ├── Order Bookings → Contract wins
   ├── Regulatory News → SEBI, RBI updates
   ├── Insider Trading → Bulk deals
   └── Stock Predictions → AI-powered forecasts

5. Email Notification
   └── Combined HTML email with all sections
```

## Key Components

### 1. Stock Service (`app/services/stock_service.py`)
Central orchestrator that coordinates:
- NSE data fetching
- Market screening
- Newsletter generation
- Portfolio analysis
- Email notifications

### 2. News Aggregator (`app/analysis/news_aggregator.py`)
Fetches and categorizes news:
- **Earnings**: Q1/Q2/Q3/Q4 results, profits
- **Orders**: Contract wins, deal announcements
- **Regulatory**: SEBI, RBI, policy changes
- **Insider**: Promoter transactions, bulk deals
- **Macro**: FII/DII, crude, gold, inflation

### 3. Technical Analysis (`app/analysis/technical.py`)
Calculates indicators:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- SMA (20, 50, 200 day)
- Bollinger Bands
- ADX (Average Directional Index)

### 4. Recommendation Engine (`app/analysis/recommendation.py`)
Generates signals with:
- Signal type: STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
- Confidence score (0-100)
- Target price & stop loss
- Risk level
- Reasons (3 per recommendation)

### 5. Market Intelligence (`app/analysis/market_intelligence.py`)
Fetches:
- FII/DII buying/selling activity
- India VIX
- Put/Call ratio
- Advance/Decline ratio
- Macro indicators (crude, gold, USD/INR)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API documentation |
| `/health` | GET | Health check |
| `/run` | GET | Run full daily scan |
| `/buy-signals` | GET | Top buy recommendations |
| `/sell-signals` | GET | Top sell recommendations |
| `/analyze-portfolio` | POST | Analyze uploaded CSV |
| `/portfolio-insights` | GET | Run portfolio analysis |
| `/test-email` | GET | Test email configuration |

## Scheduler

The application uses APScheduler for automated daily runs:

```python
# Runs at 6:55 AM IST daily
scheduler.add_job(
    func=_run_complete_daily_analysis,
    trigger=CronTrigger(hour=6, minute=55, timezone="Asia/Kolkata"),
    id="daily-complete-analysis"
)
```

Pipeline sequence:
1. Generate dashboard data
2. Run daily market scan
3. Run portfolio analysis with email

## Configuration

All configuration via environment variables:

```env
# App
APP_NAME=stock-market
PORT=8000
ENV=development
ENABLE_SCHEDULER=true

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=app-password
EMAIL_TO=recipient@example.com

# AI
GEMINI_API_KEY=your-api-key
GEMINI_MODEL=gemini-2.5-flash

# Market
NSE_INDEX_NAMES=NIFTY 100,NIFTY MIDCAP 100,NIFTY SMALLCAP 100
NEAR_52_WEEK_LOW_PCT=5.0
SEGMENT_TOP_N=20
```

## Database / Storage

The application is stateless and doesn't use a database. It:
- Fetches live data from NSE/BSE
- Scrapes news from web sources
- Caches last results in memory
- Stores dashboard data as JSON files

## Extending the System

### Adding a New News Source

1. Add source config to `SOURCES` dict in `news_aggregator.py`
2. Implement `_fetch_<source>_news()` method
3. Call it in `fetch_all_news()`

### Adding a New Indicator

1. Add calculation in `technical.py`
2. Update `TechnicalIndicators` dataclass
3. Use in `recommendation.py` for signals

### Adding a New API Endpoint

1. Add route in `app/api/routes.py`
2. Use `get_service()` for service access
3. Update root endpoint documentation
