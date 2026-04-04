"""
Newsletter Generator Module.
Generates comprehensive market newsletter with news, analysis, and predictions.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.analysis.news_aggregator import NewsAggregator, MarketNews, NewsItem
from app.analysis.market_intelligence import (
    MarketIntelligenceService, 
    MarketIntelligence,
    FundamentalData,
    FIIDIIData,
    StockFIIData,
)

logger = logging.getLogger(__name__)


@dataclass
class Newsletter:
    """Complete newsletter data."""
    date: str
    market_news: MarketNews
    market_intelligence: MarketIntelligence
    html_content: str = ""
    text_content: str = ""


class NewsletterGenerator:
    """
    Generates comprehensive market newsletter.
    
    Sections:
    1. Market Overview (indices, FII/DII, VIX)
    2. Top Stories
    3. Earnings & Results
    4. Order Bookings / Contract Wins
    5. Regulatory Updates
    6. Insider Trading / Bulk Deals
    7. Macro Indicators
    8. Top 5 Stock Movement Predictions
    """
    
    def __init__(self):
        """Initialize the newsletter generator."""
        self._news_aggregator = NewsAggregator()
        self._market_intel = MarketIntelligenceService()
    
    def generate(self) -> Newsletter:
        """
        Generate complete newsletter.
        
        Returns:
            Newsletter: Complete newsletter with HTML and text content
        """
        logger.info("Generating newsletter...")
        
        # Fetch all data
        market_news = self._news_aggregator.fetch_all_news()
        market_intel = self._market_intel.get_market_intelligence()
        
        # Create newsletter
        newsletter = Newsletter(
            date=datetime.now().strftime("%Y-%m-%d"),
            market_news=market_news,
            market_intelligence=market_intel,
        )
        
        # Generate HTML content
        newsletter.html_content = self._generate_html(newsletter)
        newsletter.text_content = self._generate_text(newsletter)
        
        logger.info(
            f"Newsletter generated: {len(market_news.top_stories)} stories, "
            f"{len(market_news.earnings_news)} earnings, "
            f"{len(market_news.stock_movements)} predictions"
        )
        
        return newsletter
    
    def _generate_html(self, newsletter: Newsletter) -> str:
        """Generate HTML newsletter content."""
        news = newsletter.market_news
        intel = newsletter.market_intelligence
        
        # Build sections
        top_stories_html = self._build_news_section(
            "📰 TOP MARKET STORIES",
            news.top_stories[:5],
            "top-stories"
        )
        
        earnings_html = self._build_news_section(
            "📊 EARNINGS & QUARTERLY RESULTS",
            news.earnings_news[:5],
            "earnings"
        )
        
        orders_html = self._build_news_section(
            "📝 ORDER BOOKINGS & CONTRACTS",
            news.order_booking_news[:5],
            "orders"
        )
        
        regulatory_html = self._build_news_section(
            "⚖️ REGULATORY & POLICY NEWS",
            news.regulatory_news[:3],
            "regulatory"
        )
        
        insider_html = self._build_news_section(
            "🔍 INSIDER TRADING & BULK DEALS",
            news.insider_trading[:3],
            "insider"
        )
        
        macro_html = self._build_macro_section(intel)
        
        predictions_html = self._build_predictions_section(news.stock_movements)
        
        html = f"""
        <div class="newsletter">
            <div class="newsletter-header">
                <h2>📈 MARKET NEWSLETTER</h2>
                <p>Daily Market Intelligence Report - {newsletter.date}</p>
            </div>
            
            {macro_html}
            {predictions_html}
            {top_stories_html}
            {earnings_html}
            {orders_html}
            {regulatory_html}
            {insider_html}
            
            <div class="newsletter-footer">
                <p><strong>Sources:</strong> MoneyControl, Economic Times, Mint, Pulse by Zerodha, Groww, BSE, NSE, Yahoo Finance</p>
                <p><em>News aggregated automatically. Verify from original sources before making investment decisions.</em></p>
            </div>
        </div>
        """
        
        return html
    
    def _build_news_section(self, title: str, items: list[NewsItem], section_class: str) -> str:
        """Build a news section HTML."""
        if not items:
            return ""
        
        rows = ""
        for item in items:
            sentiment_color = {
                "positive": "#28a745",
                "negative": "#dc3545",
                "neutral": "#6c757d"
            }.get(item.sentiment, "#6c757d")
            
            sentiment_indicator = {
                "positive": "▲",
                "negative": "▼",
                "neutral": "●"
            }.get(item.sentiment, "●")
            
            stocks_badges = ""
            for stock in item.stocks_mentioned[:3]:
                stocks_badges += f'<span class="stock-badge">{stock}</span> '
            
            rows += f"""
            <div class="news-item">
                <div class="news-sentiment" style="color: {sentiment_color};">{sentiment_indicator}</div>
                <div class="news-content">
                    <a href="{item.url}" target="_blank" class="news-headline">{item.headline}</a>
                    <div class="news-meta">
                        <span class="news-source">{item.source}</span>
                        {stocks_badges}
                    </div>
                </div>
            </div>
            """
        
        return f"""
        <div class="newsletter-section {section_class}">
            <h3>{title}</h3>
            <div class="news-list">
                {rows}
            </div>
        </div>
        """
    
    def _build_macro_section(self, intel: MarketIntelligence) -> str:
        """Build macro indicators section in table format with detailed FII/DII data."""
        
        # FII/DII colors
        fii_color = "#28a745" if intel.fii_net_buy > 0 else "#dc3545"
        dii_color = "#28a745" if intel.dii_net_buy > 0 else "#dc3545"
        fii_sign = "+" if intel.fii_net_buy > 0 else ""
        dii_sign = "+" if intel.dii_net_buy > 0 else ""
        
        # Build indicator rows for the table
        indicator_rows = ""
        for indicator in intel.macro_indicators[:4]:
            color = "#28a745" if indicator.trend == "up" else "#dc3545"
            arrow = "▲" if indicator.trend == "up" else "▼"
            impact_color = "#28a745" if indicator.impact == "positive" else "#dc3545" if indicator.impact == "negative" else "#6c757d"
            
            indicator_rows += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>{indicator.name}</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">{indicator.value}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right; color: {color};">{arrow} {abs(indicator.change_pct):.2f}%</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: center;"><span style="background: {impact_color}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 10px;">{indicator.impact.upper()}</span></td>
                </tr>
            """
        
        # Detailed FII/DII section
        fii_dii_html = self._build_fii_dii_detail_section(intel)
        
        # Top FII activity stocks
        fii_activity_html = self._build_fii_activity_section(intel)
        
        return f"""
        <div class="newsletter-section macro-section">
            <h3>🌍 MACRO INDICATORS & MARKET DATA</h3>
            
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 15px;">
                <thead>
                    <tr style="background: #f8f9fa;">
                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6;">Indicator</th>
                        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #dee2e6;">Value</th>
                        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #dee2e6;">India VIX</th>
                        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #dee2e6;">FII Net</th>
                        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #dee2e6;">DII Net</th>
                        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #dee2e6;">Crude Oil</th>
                        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #dee2e6;">Gold</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="padding: 10px; text-align: center; font-weight: bold; background: #f8f9fa;">Current</td>
                        <td style="padding: 10px; text-align: right;"></td>
                        <td style="padding: 10px; text-align: right; font-weight: bold;">{intel.india_vix}</td>
                        <td style="padding: 10px; text-align: right; font-weight: bold; color: {fii_color};">{fii_sign}₹{abs(intel.fii_net_buy):,.0f} Cr</td>
                        <td style="padding: 10px; text-align: right; font-weight: bold; color: {dii_color};">{dii_sign}₹{abs(intel.dii_net_buy):,.0f} Cr</td>
                        <td style="padding: 10px; text-align: right; font-weight: bold;">${intel.crude_oil}</td>
                        <td style="padding: 10px; text-align: right; font-weight: bold;">${intel.gold}</td>
                    </tr>
                </tbody>
            </table>
            
            {fii_dii_html}
            
            {fii_activity_html}
            
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: #e9ecef;">
                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6;">Global Indicator</th>
                        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #dee2e6;">Value</th>
                        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #dee2e6;">Change</th>
                        <th style="padding: 10px; text-align: center; border-bottom: 2px solid #dee2e6;">Market Impact</th>
                    </tr>
                </thead>
                <tbody>
                    {indicator_rows}
                </tbody>
            </table>
        </div>
        """
    
    def _build_fii_dii_detail_section(self, intel: MarketIntelligence) -> str:
        """Build detailed FII/DII activity section."""
        fii_dii = intel.fii_dii_data
        if not fii_dii:
            return ""
        
        # Calculate colors based on net values
        def get_color(val):
            return "#28a745" if val > 0 else "#dc3545" if val < 0 else "#6c757d"
        
        def format_val(val):
            sign = "+" if val > 0 else ""
            return f"{sign}₹{abs(val):,.0f} Cr"
        
        return f"""
        <div style="margin: 15px 0; padding: 15px; background: #f8f9fa; border-radius: 8px;">
            <h4 style="margin: 0 0 10px 0; color: #333;">📊 DETAILED FII/DII ACTIVITY</h4>
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: #e9ecef;">
                        <th style="padding: 8px; text-align: left; border-bottom: 2px solid #dee2e6;">Category</th>
                        <th style="padding: 8px; text-align: right; border-bottom: 2px solid #dee2e6;">Buy</th>
                        <th style="padding: 8px; text-align: right; border-bottom: 2px solid #dee2e6;">Sell</th>
                        <th style="padding: 8px; text-align: right; border-bottom: 2px solid #dee2e6;">Net</th>
                        <th style="padding: 8px; text-align: right; border-bottom: 2px solid #dee2e6;">Monthly</th>
                        <th style="padding: 8px; text-align: right; border-bottom: 2px solid #dee2e6;">YTD</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>FII/FPI</strong></td>
                        <td style="padding: 8px; text-align: right; border-bottom: 1px solid #eee;">₹{fii_dii.fii_buy_value:,.0f} Cr</td>
                        <td style="padding: 8px; text-align: right; border-bottom: 1px solid #eee;">₹{fii_dii.fii_sell_value:,.0f} Cr</td>
                        <td style="padding: 8px; text-align: right; border-bottom: 1px solid #eee; font-weight: bold; color: {get_color(fii_dii.fii_net_value)};">{format_val(fii_dii.fii_net_value)}</td>
                        <td style="padding: 8px; text-align: right; border-bottom: 1px solid #eee; color: {get_color(fii_dii.fii_monthly_net)};">{format_val(fii_dii.fii_monthly_net)}</td>
                        <td style="padding: 8px; text-align: right; border-bottom: 1px solid #eee; color: {get_color(fii_dii.fii_ytd_net)};">{format_val(fii_dii.fii_ytd_net)}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>DII</strong></td>
                        <td style="padding: 8px; text-align: right; border-bottom: 1px solid #eee;">₹{fii_dii.dii_buy_value:,.0f} Cr</td>
                        <td style="padding: 8px; text-align: right; border-bottom: 1px solid #eee;">₹{fii_dii.dii_sell_value:,.0f} Cr</td>
                        <td style="padding: 8px; text-align: right; border-bottom: 1px solid #eee; font-weight: bold; color: {get_color(fii_dii.dii_net_value)};">{format_val(fii_dii.dii_net_value)}</td>
                        <td style="padding: 8px; text-align: right; border-bottom: 1px solid #eee; color: {get_color(fii_dii.dii_monthly_net)};">{format_val(fii_dii.dii_monthly_net)}</td>
                        <td style="padding: 8px; text-align: right; border-bottom: 1px solid #eee;">-</td>
                    </tr>
                </tbody>
            </table>
            <p style="margin: 10px 0 0 0; font-size: 11px; color: #666;">
                Data as of {fii_dii.date}. Source: NSDL, NSE, MoneyControl
            </p>
        </div>
        """
    
    def _build_fii_activity_section(self, intel: MarketIntelligence) -> str:
        """Build top FII buying/selling stocks section."""
        if not intel.top_fii_buys and not intel.top_fii_sells:
            return ""
        
        buy_rows = ""
        for stock in intel.top_fii_buys[:5]:
            change_color = "#28a745" if stock.fii_holding_change > 0 else "#dc3545"
            change_sign = "+" if stock.fii_holding_change > 0 else ""
            buy_rows += f"""
                <tr>
                    <td style="padding: 6px; border-bottom: 1px solid #eee;">{stock.symbol}</td>
                    <td style="padding: 6px; text-align: right; border-bottom: 1px solid #eee;">{stock.fii_holding_pct:.1f}%</td>
                    <td style="padding: 6px; text-align: right; border-bottom: 1px solid #eee; color: {change_color};">{change_sign}{stock.fii_holding_change:.2f}%</td>
                </tr>
            """
        
        sell_rows = ""
        for stock in intel.top_fii_sells[:5]:
            change_color = "#28a745" if stock.fii_holding_change > 0 else "#dc3545"
            change_sign = "+" if stock.fii_holding_change > 0 else ""
            sell_rows += f"""
                <tr>
                    <td style="padding: 6px; border-bottom: 1px solid #eee;">{stock.symbol}</td>
                    <td style="padding: 6px; text-align: right; border-bottom: 1px solid #eee;">{stock.fii_holding_pct:.1f}%</td>
                    <td style="padding: 6px; text-align: right; border-bottom: 1px solid #eee; color: {change_color};">{change_sign}{stock.fii_holding_change:.2f}%</td>
                </tr>
            """
        
        buy_section = ""
        if buy_rows:
            buy_section = f"""
            <div style="flex: 1; min-width: 200px;">
                <h5 style="margin: 0 0 8px 0; color: #28a745;">🔼 FII Buying</h5>
                <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                    <thead>
                        <tr style="background: #e8f5e9;">
                            <th style="padding: 6px; text-align: left;">Stock</th>
                            <th style="padding: 6px; text-align: right;">Holding</th>
                            <th style="padding: 6px; text-align: right;">Change</th>
                        </tr>
                    </thead>
                    <tbody>
                        {buy_rows}
                    </tbody>
                </table>
            </div>
            """
        
        sell_section = ""
        if sell_rows:
            sell_section = f"""
            <div style="flex: 1; min-width: 200px;">
                <h5 style="margin: 0 0 8px 0; color: #dc3545;">🔽 FII Selling</h5>
                <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                    <thead>
                        <tr style="background: #ffebee;">
                            <th style="padding: 6px; text-align: left;">Stock</th>
                            <th style="padding: 6px; text-align: right;">Holding</th>
                            <th style="padding: 6px; text-align: right;">Change</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sell_rows}
                    </tbody>
                </table>
            </div>
            """
        
        return f"""
        <div style="margin: 15px 0; padding: 15px; background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;">
            <h4 style="margin: 0 0 15px 0; color: #333;">🏦 FII STOCK-WISE ACTIVITY (QoQ Change)</h4>
            <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                {buy_section}
                {sell_section}
            </div>
            <p style="margin: 10px 0 0 0; font-size: 11px; color: #666;">
                Based on latest quarterly shareholding data from Screener.in/NSDL
            </p>
        </div>
        """
    
    def _build_predictions_section(self, predictions: list[dict]) -> str:
        """Build stock movement predictions section."""
        if not predictions:
            return ""
        
        rows = ""
        for i, pred in enumerate(predictions, 1):
            direction_color = "#28a745" if pred["direction"] == "UP" else "#dc3545"
            direction_arrow = "▲" if pred["direction"] == "UP" else "▼"
            
            rows += f"""
            <tr>
                <td>{i}</td>
                <td><strong>{pred['stock']}</strong></td>
                <td style="color: {direction_color}; font-weight: bold;">{direction_arrow} {pred['direction']}</td>
                <td>{pred['confidence']}%</td>
                <td><small>{pred['reason'][:60]}...</small></td>
            </tr>
            """
        
        return f"""
        <div class="newsletter-section predictions-section">
            <h3>🎯 TOP 5 STOCK MOVEMENT PREDICTIONS</h3>
            <p class="section-subtitle">Based on news sentiment and market events</p>
            <table class="predictions-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Stock</th>
                        <th>Expected Move</th>
                        <th>Confidence</th>
                        <th>Key Driver</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        """
    
    def _generate_text(self, newsletter: Newsletter) -> str:
        """Generate plain text newsletter content."""
        news = newsletter.market_news
        intel = newsletter.market_intelligence
        
        lines = [
            "=" * 60,
            "MARKET NEWSLETTER",
            f"Daily Intelligence Report - {newsletter.date}",
            "=" * 60,
            "",
            "MACRO INDICATORS",
            "-" * 40,
            f"India VIX: {intel.india_vix}",
            f"FII Net: ₹{intel.fii_net_buy:,.0f} Cr",
            f"DII Net: ₹{intel.dii_net_buy:,.0f} Cr",
            f"Crude Oil: ${intel.crude_oil}",
            f"Gold: ${intel.gold}",
            "",
        ]
        
        # Detailed FII/DII data
        if intel.fii_dii_data:
            fii_dii = intel.fii_dii_data
            lines.extend([
                "DETAILED FII/DII ACTIVITY",
                "-" * 40,
                f"FII/FPI:",
                f"  Buy: ₹{fii_dii.fii_buy_value:,.0f} Cr | Sell: ₹{fii_dii.fii_sell_value:,.0f} Cr | Net: ₹{fii_dii.fii_net_value:,.0f} Cr",
                f"  Monthly: ₹{fii_dii.fii_monthly_net:,.0f} Cr | YTD: ₹{fii_dii.fii_ytd_net:,.0f} Cr",
                f"DII:",
                f"  Buy: ₹{fii_dii.dii_buy_value:,.0f} Cr | Sell: ₹{fii_dii.dii_sell_value:,.0f} Cr | Net: ₹{fii_dii.dii_net_value:,.0f} Cr",
                f"  Monthly: ₹{fii_dii.dii_monthly_net:,.0f} Cr",
                "",
            ])
        
        # FII stock activity
        if intel.top_fii_buys:
            lines.extend([
                "TOP FII BUYING STOCKS",
                "-" * 40,
            ])
            for stock in intel.top_fii_buys[:5]:
                sign = "+" if stock.fii_holding_change > 0 else ""
                lines.append(f"  {stock.symbol}: {stock.fii_holding_pct:.1f}% ({sign}{stock.fii_holding_change:.2f}%)")
            lines.append("")
        
        if intel.top_fii_sells:
            lines.extend([
                "TOP FII SELLING STOCKS",
                "-" * 40,
            ])
            for stock in intel.top_fii_sells[:5]:
                sign = "+" if stock.fii_holding_change > 0 else ""
                lines.append(f"  {stock.symbol}: {stock.fii_holding_pct:.1f}% ({sign}{stock.fii_holding_change:.2f}%)")
            lines.append("")
        
        # Stock Predictions
        if news.stock_movements:
            lines.extend([
                "TOP 5 STOCK MOVEMENT PREDICTIONS",
                "-" * 40,
            ])
            for i, pred in enumerate(news.stock_movements, 1):
                arrow = "▲" if pred["direction"] == "UP" else "▼"
                lines.append(f"{i}. {pred['stock']} {arrow} {pred['direction']} ({pred['confidence']}%)")
                lines.append(f"   Reason: {pred['reason'][:50]}...")
            lines.append("")
        
        # Top Stories
        if news.top_stories:
            lines.extend([
                "TOP MARKET STORIES",
                "-" * 40,
            ])
            for item in news.top_stories[:5]:
                lines.append(f"• {item.headline[:70]}...")
                lines.append(f"  Source: {item.source}")
            lines.append("")
        
        # Earnings
        if news.earnings_news:
            lines.extend([
                "EARNINGS & RESULTS",
                "-" * 40,
            ])
            for item in news.earnings_news[:3]:
                lines.append(f"• {item.headline[:70]}...")
            lines.append("")
        
        # Order Bookings
        if news.order_booking_news:
            lines.extend([
                "ORDER BOOKINGS & CONTRACTS",
                "-" * 40,
            ])
            for item in news.order_booking_news[:3]:
                lines.append(f"• {item.headline[:70]}...")
            lines.append("")
        
        lines.extend([
            "=" * 60,
            "Sources: MoneyControl, Economic Times, Mint, Pulse by Zerodha,",
            "         Groww, BSE, NSE, NSDL, Screener.in, Yahoo Finance",
            "=" * 60,
        ])
        
        return "\n".join(lines)
    
    def get_newsletter_css(self) -> str:
        """Get CSS styles for newsletter sections."""
        return """
            .newsletter {
                background: white;
                border-radius: 10px;
                padding: 0;
                margin-bottom: 25px;
            }
            .newsletter-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px 10px 0 0;
                text-align: center;
            }
            .newsletter-header h2 {
                margin: 0;
                font-size: 20px;
            }
            .newsletter-header p {
                margin: 5px 0 0 0;
                opacity: 0.9;
            }
            .newsletter-section {
                padding: 20px;
                border-bottom: 1px solid #eee;
            }
            .newsletter-section h3 {
                margin: 0 0 15px 0;
                color: #1a1a2e;
                font-size: 16px;
            }
            .section-subtitle {
                margin: -10px 0 15px 0;
                color: #666;
                font-size: 12px;
            }
            .news-list {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            .news-item {
                display: flex;
                align-items: flex-start;
                gap: 10px;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 6px;
            }
            .news-sentiment {
                font-size: 16px;
                font-weight: bold;
            }
            .news-content {
                flex: 1;
            }
            .news-headline {
                color: #1a1a2e;
                text-decoration: none;
                font-size: 13px;
                line-height: 1.4;
            }
            .news-headline:hover {
                color: #667eea;
            }
            .news-meta {
                margin-top: 5px;
                font-size: 11px;
            }
            .news-source {
                color: #666;
                margin-right: 10px;
            }
            .stock-badge {
                background: #e9ecef;
                color: #495057;
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 10px;
                margin-right: 4px;
            }
            .macro-section .market-data-row {
                display: flex;
                justify-content: space-between;
                flex-wrap: wrap;
                gap: 10px;
                margin-bottom: 15px;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 8px;
            }
            .market-data-item {
                text-align: center;
            }
            .market-data-item .label {
                display: block;
                font-size: 11px;
                color: #666;
            }
            .market-data-item .value {
                display: block;
                font-size: 14px;
                font-weight: bold;
            }
            .macro-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 10px;
            }
            .macro-item {
                background: #f8f9fa;
                padding: 10px;
                border-radius: 6px;
                text-align: center;
            }
            .macro-name {
                font-size: 11px;
                color: #666;
            }
            .macro-value {
                font-size: 16px;
                font-weight: bold;
            }
            .macro-change {
                font-size: 12px;
            }
            .impact-positive { color: #28a745; font-size: 10px; }
            .impact-negative { color: #dc3545; font-size: 10px; }
            .impact-neutral { color: #6c757d; font-size: 10px; }
            .predictions-section {
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            }
            .predictions-table {
                width: 100%;
                border-collapse: collapse;
            }
            .predictions-table th {
                background: #dee2e6;
                padding: 8px;
                text-align: left;
                font-size: 12px;
            }
            .predictions-table td {
                padding: 8px;
                border-bottom: 1px solid #dee2e6;
                font-size: 12px;
            }
            .newsletter-footer {
                padding: 15px 20px;
                background: #f8f9fa;
                border-radius: 0 0 10px 10px;
                font-size: 11px;
                color: #666;
            }
            .newsletter-footer p {
                margin: 5px 0;
            }
        """
