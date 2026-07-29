# GitHub Copilot Instructions for Stock Market Project

## Project Context
This is a FastAPI-based automated stock market analysis system for Indian NSE/BSE stocks. It runs daily scans at 6:55 AM IST, fetches news from multiple sources, and sends email newsletters.

## Code Style Guidelines
- Use Python 3.11+ features
- Follow PEP 8 naming conventions
- Use type hints for all function parameters and return values
- Prefer dataclasses for data structures
- Use logging module for all log messages (not print statements)
- Handle exceptions gracefully with proper error logging

## Architecture Patterns
- **Dependency Injection**: Services are injected via constructors
- **Singleton Pattern**: Settings and service instances are singletons
- **Strategy Pattern**: Different screeners (buy/sell/recovery) implement screening logic
- **Factory Pattern**: FastAPI app created via `create_app()` function

## Key Modules Reference
| Module | Purpose |
|--------|---------|
| `app/analysis/technical.py` | Technical indicators (RSI, MACD, SMA, Bollinger) |
| `app/analysis/recommendation.py` | Buy/Sell signal generation with confidence scores |
| `app/analysis/news_aggregator.py` | Multi-source news fetching and categorization |
| `app/analysis/market_intelligence.py` | FII/DII data, macro indicators |
| `app/analysis/newsletter.py` | HTML/text newsletter generation |
| `app/data/nse_client.py` | NSE stock data fetching |
| `app/scheduler/jobs.py` | APScheduler job definitions |

## News Categories
When working with news, categorize into:
- `earnings`: Quarterly results, profit/loss (keywords: Q1, Q2, Q3, Q4, results, profit)
- `orders`: Contract wins, order bookings (keywords: order, contract, wins, bags)
- `regulatory`: SEBI, RBI, policy (keywords: sebi, rbi, government, regulation)
- `insider`: Bulk deals, promoter activity (keywords: promoter, stake, bulk deal)
- `macro`: Economic indicators (keywords: inflation, gdp, fii, dii, crude)

## API Response Format
All API responses should follow this structure:
```python
{
    "status": "success" | "error",
    "data": {...},  # or list
    "message": "Optional message"
}
```

## Testing Conventions
- Test files in `tests/` directory
- Use pytest for testing
- Mock external API calls (NSE, news sources)
- Test file naming: `test_<module_name>.py`

## Environment Variables
Always use `app.config.settings` for configuration. Never hardcode:
- API keys (`GEMINI_API_KEY`)
- Email credentials (`SMTP_*`)
- URLs (use settings.dashboard_url)

## Common Tasks

### Adding a New News Source
1. Add source config to `NEWS_AGGREGATOR.SOURCES` dict
2. Create `_fetch_<source>_news()` method
3. Add to `fetch_all_news()` aggregation

### Adding a New Technical Indicator
1. Add calculation in `app/analysis/technical.py`
2. Update `TechnicalIndicators` dataclass
3. Use in `recommendation.py` for signals

### Adding a New API Endpoint
1. Add route in `app/api/routes.py`
2. Use `get_service()` for StockService access
3. Update root endpoint documentation
