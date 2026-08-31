"""
Portfolio Email Generator.
Generates HTML and text emails for portfolio analysis.
Uses modern inline CSS template for email client compatibility.
"""

import logging
from datetime import datetime
from typing import Optional

from app.config import settings
from app.analysis.portfolio_insights import (
    PortfolioInsights,
    PortfolioSignal,
    HoldingAnalysis,
    RiskLevel,
    DeclineSummary,
    DetailedBuyRecommendation,
)

logger = logging.getLogger(__name__)


class PortfolioEmailGenerator:
    """Generate portfolio analysis emails with modern template."""
    
    def generate_html(self, insights: PortfolioInsights) -> str:
        """Generate HTML email content using Sample 5 template."""
        summary = insights.summary
        
        # Fetch market overview data
        market_data = self._fetch_market_overview()
        
        # Build email sections
        header_html = self._build_modern_header(insights, market_data)
        outlook_html = self._build_market_outlook(insights, market_data)
        indices_html = self._build_global_indices(market_data)
        indicators_html = self._build_market_indicators(market_data)
        predictions_html = self._build_top5_predictions(market_data)
        headlines_html = self._build_news_headlines(insights)
        earnings_html = self._build_earnings_news(insights)
        regulatory_html = self._build_regulatory_news(insights)
        portfolio_analysis_html = self._build_portfolio_analysis(insights)
        action_alerts_html = self._build_action_alerts(insights)
        holdings_predictions_html = self._build_holdings_predictions(insights)
        gainers_losers_html = self._build_gainers_losers(insights)
        risk_alerts_html = self._build_risk_alerts(insights)
        strategy_html = self._build_strategy_section(insights)
        footer_html = self._build_footer(insights)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Market Daily Prediction</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5;">
        <tr>
            <td align="center" style="padding: 16px;">
                <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 12px; overflow: hidden;">
                    
                    {header_html}
                    {outlook_html}
                    {indices_html}
                    {indicators_html}
                    {predictions_html}
                    {headlines_html}
                    {earnings_html}
                    {regulatory_html}
                    {portfolio_analysis_html}
                    {action_alerts_html}
                    {holdings_predictions_html}
                    {gainers_losers_html}
                    {risk_alerts_html}
                    {strategy_html}
                    {footer_html}

                </table>
            </td>
        </tr>
    </table>

</body>
</html>"""
        
        return html
    
    def _fetch_market_overview(self) -> dict:
        """Fetch live market data."""
        try:
            from app.analysis.market_overview import MarketOverviewFetcher
            from app.analysis.market_intelligence import MarketIntelligenceService
            from app.analysis.news_aggregator import NewsAggregator
            
            # Fetch market overview
            overview_fetcher = MarketOverviewFetcher()
            overview = overview_fetcher.get_overview()
            
            # Fetch market intelligence (FII/DII, VIX, etc.)
            intel_service = MarketIntelligenceService()
            intel = intel_service.get_market_intelligence()
            
            # Fetch news aggregator for general market predictions
            news_aggregator = NewsAggregator()
            market_news = news_aggregator.fetch_all_news()
            
            return {
                "sensex": overview.sensex,
                "nifty": overview.nifty,
                "dow": overview.dow_jones,
                "nasdaq": overview.nasdaq,
                "usd_inr": overview.usd_inr,
                "market_outlook": overview.market_outlook,
                "outlook_reason": overview.outlook_reason,
                "fii_net": intel.fii_net_buy if intel else 0,
                "dii_net": intel.dii_net_buy if intel else 0,
                "vix": intel.india_vix if intel else 0,
                "crude": intel.crude_oil if intel else 0,
                "gold": intel.gold if intel else 0,
                "stock_movements": market_news.stock_movements if market_news else [],
            }
        except Exception as e:
            logger.warning(f"Failed to fetch market data: {e}")
            return {}
    
    def _build_modern_header(self, insights: PortfolioInsights, market_data: dict) -> str:
        """Build modern header with portfolio summary."""
        summary = insights.summary
        pnl_color = "#f87171" if summary.total_pnl < 0 else "#4ade80"
        pnl_sign = "" if summary.total_pnl < 0 else "+"
        
        return f"""
                    <!-- Header -->
                    <tr>
                        <td style="background: #0f172a; padding: 20px 24px;">
                            <table role="presentation" width="100%">
                                <tr>
                                    <td>
                                        <span style="font-size: 20px; font-weight: 700; color: #ffffff;">📈 Daily Market Prediction</span>
                                        <span style="display: block; color: #94a3b8; font-size: 13px; margin-top: 4px;">{insights.date}</span>
                                    </td>
                                    <td style="text-align: right;">
                                        <span style="display: block; color: #fbbf24; font-size: 11px;">Your Portfolio</span>
                                        <span style="color: {pnl_color}; font-size: 14px; font-weight: 700;">₹{summary.current_value/100000:.2f}L ({pnl_sign}{summary.total_pnl_pct:.1f}%)</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>"""
    
    def _build_market_outlook(self, insights: PortfolioInsights, market_data: dict) -> str:
        """Build market outlook banner."""
        outlook = market_data.get("market_outlook", "NEUTRAL")
        reason = market_data.get("outlook_reason", "")
        
        # Determine color based on outlook
        if "BULLISH" in outlook.upper():
            bg_color = "linear-gradient(135deg, #059669 0%, #10b981 100%)"
            emoji = "🚀"
        elif "BEARISH" in outlook.upper():
            bg_color = "linear-gradient(135deg, #dc2626 0%, #ef4444 100%)"
            emoji = "📉"
        else:
            bg_color = "linear-gradient(135deg, #d97706 0%, #f59e0b 100%)"
            emoji = "⚖️"
        
        # Build subtitle with market cues
        dow = market_data.get("dow")
        nasdaq = market_data.get("nasdaq")
        subtitle_parts = []
        if dow:
            arrow = "▲" if dow.is_up else "▼"
            subtitle_parts.append(f"Dow {arrow}{abs(dow.change_pct):.1f}%")
        if nasdaq:
            arrow = "▲" if nasdaq.is_up else "▼"
            subtitle_parts.append(f"NASDAQ {arrow}{abs(nasdaq.change_pct):.1f}%")
        subtitle = " • ".join(subtitle_parts) if subtitle_parts else ""
        
        return f"""
                    <!-- Market Outlook Banner -->
                    <tr>
                        <td style="padding: 16px;">
                            <table role="presentation" width="100%" style="background: {bg_color}; border-radius: 10px;">
                                <tr>
                                    <td style="padding: 16px; text-align: center;">
                                        <span style="color: rgba(255,255,255,0.85); font-size: 11px; text-transform: uppercase; letter-spacing: 2px;">Today's Outlook</span>
                                        <span style="display: block; color: #ffffff; font-size: 26px; font-weight: 800; margin: 4px 0;">{emoji} {outlook}</span>
                                        <span style="color: rgba(255,255,255,0.9); font-size: 12px;">{subtitle}</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>"""
    
    def _build_global_indices(self, market_data: dict) -> str:
        """Build global market indices row."""
        def build_index_cell(idx, label: str, emoji: str) -> str:
            if not idx:
                return f"""
                                    <td width="20%" style="background: #f1f5f9; border-radius: 8px; padding: 10px 6px; text-align: center;">
                                        <span style="display: block; font-size: 10px; color: #64748b; text-transform: uppercase;">{emoji} {label}</span>
                                        <span style="display: block; font-size: 15px; font-weight: 700; color: #0f172a;">--</span>
                                        <span style="font-size: 11px; color: #64748b; font-weight: 600;">--</span>
                                    </td>"""
            
            change_color = "#22c55e" if idx.is_up else "#ef4444"
            arrow = "▲" if idx.is_up else "▼"
            
            # Format value based on type
            if label == "USD/INR":
                value = f"₹{idx.last_close:.2f}"
            else:
                value = f"{idx.last_close:,.0f}"
            
            return f"""
                                    <td width="20%" style="background: #f1f5f9; border-radius: 8px; padding: 10px 6px; text-align: center;">
                                        <span style="display: block; font-size: 10px; color: #64748b; text-transform: uppercase;">{emoji} {label}</span>
                                        <span style="display: block; font-size: 15px; font-weight: 700; color: #0f172a;">{value}</span>
                                        <span style="font-size: 11px; color: {change_color}; font-weight: 600;">{arrow} {abs(idx.change_pct):.2f}%</span>
                                    </td>"""
        
        sensex_cell = build_index_cell(market_data.get("sensex"), "Sensex", "🇮🇳")
        nifty_cell = build_index_cell(market_data.get("nifty"), "Nifty", "🇮🇳")
        dow_cell = build_index_cell(market_data.get("dow"), "Dow", "🇺🇸")
        nasdaq_cell = build_index_cell(market_data.get("nasdaq"), "NASDAQ", "🇺🇸")
        usd_cell = build_index_cell(market_data.get("usd_inr"), "USD/INR", "💱")
        
        return f"""
                    <!-- Global Markets - Compact Pills -->
                    <tr>
                        <td style="padding: 0 16px 16px 16px;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="4">
                                <tr>
                                    {sensex_cell}
                                    {nifty_cell}
                                    {dow_cell}
                                    {nasdaq_cell}
                                    {usd_cell}
                                </tr>
                            </table>
                        </td>
                    </tr>"""
    
    def _build_market_indicators(self, market_data: dict) -> str:
        """Build market indicators row (VIX, FII, DII, Crude, Gold)."""
        vix = market_data.get("vix", 0)
        fii = market_data.get("fii_net", 0)
        dii = market_data.get("dii_net", 0)
        crude = market_data.get("crude", 0)
        gold = market_data.get("gold", 0)
        
        # Determine colors based on values
        vix_bg = "#ecfdf5" if vix < 18 else "#fef2f2" if vix > 25 else "#f1f5f9"
        vix_color = "#059669" if vix < 18 else "#dc2626" if vix > 25 else "#64748b"
        
        fii_bg = "#ecfdf5" if fii > 0 else "#fef2f2"
        fii_color = "#059669" if fii > 0 else "#dc2626"
        fii_sign = "+" if fii >= 0 else ""
        
        dii_bg = "#ecfdf5" if dii > 0 else "#fef2f2"
        dii_color = "#059669" if dii > 0 else "#dc2626"
        dii_sign = "+" if dii >= 0 else ""
        
        return f"""
                    <!-- Institutional Activity - Icon Pills -->
                    <tr>
                        <td style="padding: 0 16px 16px 16px;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="4">
                                <tr>
                                    <td width="20%" style="background: {vix_bg}; border-radius: 8px; padding: 10px 6px; text-align: center;">
                                        <span style="display: block; font-size: 18px;">😌</span>
                                        <span style="display: block; font-size: 10px; color: {vix_color}; font-weight: 600;">VIX</span>
                                        <span style="display: block; font-size: 14px; font-weight: 700; color: {vix_color};">{vix:.2f}</span>
                                    </td>
                                    <td width="20%" style="background: {fii_bg}; border-radius: 8px; padding: 10px 6px; text-align: center;">
                                        <span style="display: block; font-size: 18px;">🏦</span>
                                        <span style="display: block; font-size: 10px; color: {fii_color}; font-weight: 600;">FII</span>
                                        <span style="display: block; font-size: 14px; font-weight: 700; color: {fii_color};">{fii_sign}₹{abs(fii):.0f}Cr</span>
                                    </td>
                                    <td width="20%" style="background: {dii_bg}; border-radius: 8px; padding: 10px 6px; text-align: center;">
                                        <span style="display: block; font-size: 18px;">🏠</span>
                                        <span style="display: block; font-size: 10px; color: {dii_color}; font-weight: 600;">DII</span>
                                        <span style="display: block; font-size: 14px; font-weight: 700; color: {dii_color};">{dii_sign}₹{abs(dii):.0f}Cr</span>
                                    </td>
                                    <td width="20%" style="background: #f1f5f9; border-radius: 8px; padding: 10px 6px; text-align: center;">
                                        <span style="display: block; font-size: 18px;">🛢️</span>
                                        <span style="display: block; font-size: 10px; color: #64748b; font-weight: 600;">Crude</span>
                                        <span style="display: block; font-size: 14px; font-weight: 700; color: #0f172a;">${crude:.2f}</span>
                                    </td>
                                    <td width="20%" style="background: #fef3c7; border-radius: 8px; padding: 10px 6px; text-align: center;">
                                        <span style="display: block; font-size: 18px;">🥇</span>
                                        <span style="display: block; font-size: 10px; color: #b45309; font-weight: 600;">Gold</span>
                                        <span style="display: block; font-size: 14px; font-weight: 700; color: #b45309;">${gold:,.0f}</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>"""
    
    def _build_top5_predictions(self, market_data: dict) -> str:
        """Build top 5 general stock movement predictions from news sentiment."""
        predictions = market_data.get("stock_movements", [])[:5]
        if not predictions:
            return ""
        
        rows = ""
        for pred in predictions:
            direction = pred.get("direction", "HOLD")
            if direction == "UP":
                arrow = "▲"
                color = "#22c55e"
                bg = "#22c55e"
            elif direction == "DOWN":
                arrow = "▼"
                color = "#ef4444"
                bg = "#ef4444"
            else:
                arrow = "●"
                color = "#f59e0b"
                bg = "#f59e0b"
            
            stock = pred.get("stock", "")
            confidence = pred.get("confidence", 50)
            reason = pred.get("reason", "")[:30]
            
            rows += f"""
                                            <tr>
                                                <td style="padding: 8px 0; border-bottom: 1px solid #1e293b;">
                                                    <table role="presentation" width="100%">
                                                        <tr>
                                                            <td width="8%" style="text-align: center;"><span style="color: {color}; font-size: 16px;">{arrow}</span></td>
                                                            <td width="28%"><span style="color: #ffffff; font-size: 14px; font-weight: 700;">{stock}</span></td>
                                                            <td width="24%"><span style="display: inline-block; background: {bg}; color: #ffffff; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 600;">{confidence:.0f}% CONF</span></td>
                                                            <td><span style="color: #94a3b8; font-size: 11px;">{reason}</span></td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>"""
        
        return f"""
                    <!-- 🎯 TOP 5 STOCK MOVEMENT PREDICTIONS -->
                    <tr>
                        <td style="padding: 0 16px 16px 16px;">
                            <table role="presentation" width="100%" style="background: #0f172a; border-radius: 10px;">
                                <tr>
                                    <td style="padding: 14px;">
                                        <span style="display: block; color: #ffffff; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;">🎯 Top 5 Stock Movement Predictions</span>
                                        
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                            {rows}
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>"""
    
    def _build_news_headlines(self, insights: PortfolioInsights) -> str:
        """Build today's headlines section."""
        # Filter general market news
        news = [n for n in insights.portfolio_news if n.sentiment in ["positive", "neutral"]][:4]
        if not news:
            return ""
        
        rows = ""
        for item in news:
            if item.sentiment == "positive":
                color = "#22c55e"
                icon = "▲"
            elif item.sentiment == "negative":
                color = "#ef4444"
                icon = "▼"
            else:
                color = "#64748b"
                icon = "●"
            
            # Truncate headline
            headline = item.headline[:70] + "..." if len(item.headline) > 70 else item.headline
            
            rows += f"""
                                <tr>
                                    <td style="padding: 10px 12px; border-bottom: 1px solid #e2e8f0;">
                                        <span style="color: {color}; font-weight: 700; margin-right: 6px;">{icon}</span>
                                        <a href="{item.url}" style="color: #0f172a; font-size: 13px; text-decoration: none;">{headline}</a>
                                        <span style="color: #94a3b8; font-size: 10px;"> — {item.source}</span>
                                    </td>
                                </tr>"""
        
        return f"""
                    <!-- 📰 Today's Headlines -->
                    <tr>
                        <td style="padding: 0 16px 12px 16px;">
                            <span style="display: block; font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">📰 Today's Headlines</span>
                            
                            <table role="presentation" width="100%" style="background: #f8fafc; border-radius: 8px;">
                                {rows}
                            </table>
                        </td>
                    </tr>"""
    
    def _build_earnings_news(self, insights: PortfolioInsights) -> str:
        """Build earnings & quarterly results section."""
        # Filter earnings-related news
        earnings_keywords = ["Q1", "Q2", "Q3", "Q4", "quarterly", "results", "earnings", "profit", "revenue"]
        earnings_news = []
        
        for item in insights.portfolio_news:
            if any(kw.lower() in item.headline.lower() for kw in earnings_keywords):
                earnings_news.append(item)
        
        if not earnings_news:
            return ""
        
        rows = ""
        for item in earnings_news[:3]:
            if item.sentiment == "positive":
                color = "#22c55e"
                icon = "▲"
            elif item.sentiment == "negative":
                color = "#ef4444"
                icon = "▼"
            else:
                color = "#64748b"
                icon = "●"
            
            headline = item.headline[:65] + "..." if len(item.headline) > 65 else item.headline
            stocks = " ".join([f"<span style='color: #991b1b; font-size: 10px;'>⚠️ You hold {s}</span>" for s in item.stocks_mentioned[:1]]) if item.stocks_mentioned else ""
            
            rows += f"""
                                <tr>
                                    <td style="padding: 10px 12px; border-bottom: 1px solid #fecaca;">
                                        <span style="color: {color}; font-weight: 700; margin-right: 6px;">{icon}</span>
                                        <a href="{item.url}" style="color: #0f172a; font-size: 13px; text-decoration: none;">{headline}</a>
                                        <span style="display: block; color: #64748b; font-size: 10px; margin-top: 2px;">{stocks}</span>
                                    </td>
                                </tr>"""
        
        return f"""
                    <!-- 📊 Earnings & Quarterly Results -->
                    <tr>
                        <td style="padding: 0 16px 12px 16px;">
                            <span style="display: block; font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">📊 Earnings & Quarterly Results</span>
                            
                            <table role="presentation" width="100%" style="background: #fef2f2; border-radius: 8px; border-left: 3px solid #ef4444;">
                                {rows}
                            </table>
                        </td>
                    </tr>"""
    
    def _build_regulatory_news(self, insights: PortfolioInsights) -> str:
        """Build regulatory & policy news section."""
        # Filter regulatory news
        reg_keywords = ["SEBI", "RBI", "government", "regulation", "policy", "IPO", "DRHP", "banking"]
        reg_news = []
        
        for item in insights.portfolio_news:
            if any(kw.lower() in item.headline.lower() for kw in reg_keywords):
                reg_news.append(item)
        
        if not reg_news:
            return ""
        
        rows = ""
        for item in reg_news[:2]:
            headline = item.headline[:65] + "..." if len(item.headline) > 65 else item.headline
            
            rows += f"""
                                <tr>
                                    <td style="padding: 10px 12px; border-bottom: 1px solid #e2e8f0;">
                                        <span style="color: #64748b; font-weight: 700; margin-right: 6px;">●</span>
                                        <a href="{item.url}" style="color: #0f172a; font-size: 13px; text-decoration: none;">{headline}</a>
                                        <span style="display: block; color: #64748b; font-size: 10px; margin-top: 2px;">{item.source}</span>
                                    </td>
                                </tr>"""
        
        return f"""
                    <!-- ⚖️ Regulatory & Policy News -->
                    <tr>
                        <td style="padding: 0 16px 12px 16px;">
                            <span style="display: block; font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">⚖️ Regulatory & Policy News</span>
                            
                            <table role="presentation" width="100%" style="background: #f8fafc; border-radius: 8px;">
                                {rows}
                            </table>
                        </td>
                    </tr>"""
    
    def _build_portfolio_analysis(self, insights: PortfolioInsights) -> str:
        """Build portfolio analysis card."""
        summary = insights.summary
        
        pnl_bg = "rgba(239,68,68,0.3)" if summary.total_pnl < 0 else "rgba(34,197,94,0.3)"
        pnl_color = "#fca5a5" if summary.total_pnl < 0 else "#86efac"
        pnl_sign = "" if summary.total_pnl < 0 else "+"
        
        day_color = "#86efac" if summary.day_change >= 0 else "#fca5a5"
        day_sign = "+" if summary.day_change >= 0 else ""
        
        return f"""
                    <!-- 📊 PORTFOLIO ANALYSIS -->
                    <tr>
                        <td style="padding: 0 16px 12px 16px;">
                            <table role="presentation" width="100%" style="background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%); border-radius: 10px;">
                                <tr>
                                    <td style="padding: 16px;">
                                        <span style="display: block; color: rgba(255,255,255,0.9); font-size: 11px; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 10px;">📊 Portfolio Analysis</span>
                                        
                                        <!-- Portfolio Summary Row -->
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="6" style="margin-bottom: 12px;">
                                            <tr>
                                                <td width="25%" style="background: rgba(255,255,255,0.15); border-radius: 8px; padding: 10px; text-align: center;">
                                                    <span style="display: block; color: rgba(255,255,255,0.7); font-size: 10px;">Invested</span>
                                                    <span style="display: block; color: #ffffff; font-size: 16px; font-weight: 700;">₹{summary.total_investment/100000:.2f}L</span>
                                                </td>
                                                <td width="25%" style="background: rgba(255,255,255,0.15); border-radius: 8px; padding: 10px; text-align: center;">
                                                    <span style="display: block; color: rgba(255,255,255,0.7); font-size: 10px;">Current</span>
                                                    <span style="display: block; color: #ffffff; font-size: 16px; font-weight: 700;">₹{summary.current_value/100000:.2f}L</span>
                                                </td>
                                                <td width="25%" style="background: {pnl_bg}; border-radius: 8px; padding: 10px; text-align: center;">
                                                    <span style="display: block; color: rgba(255,255,255,0.7); font-size: 10px;">P&L</span>
                                                    <span style="display: block; color: {pnl_color}; font-size: 16px; font-weight: 700;">{pnl_sign}₹{abs(summary.total_pnl)/100000:.2f}L</span>
                                                </td>
                                                <td width="25%" style="background: {pnl_bg}; border-radius: 8px; padding: 10px; text-align: center;">
                                                    <span style="display: block; color: rgba(255,255,255,0.7); font-size: 10px;">Returns</span>
                                                    <span style="display: block; color: {pnl_color}; font-size: 16px; font-weight: 700;">{pnl_sign}{summary.total_pnl_pct:.1f}%</span>
                                                </td>
                                            </tr>
                                        </table>

                                        <!-- Holdings Stats -->
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="6">
                                            <tr>
                                                <td width="33%" style="background: rgba(34,197,94,0.2); border-radius: 6px; padding: 8px; text-align: center;">
                                                    <span style="color: #86efac; font-size: 18px; font-weight: 700;">{summary.profitable_stocks}</span>
                                                    <span style="display: block; color: #86efac; font-size: 10px;">Stocks in Profit</span>
                                                </td>
                                                <td width="33%" style="background: rgba(239,68,68,0.2); border-radius: 6px; padding: 8px; text-align: center;">
                                                    <span style="color: #fca5a5; font-size: 18px; font-weight: 700;">{summary.loss_making_stocks}</span>
                                                    <span style="display: block; color: #fca5a5; font-size: 10px;">Stocks in Loss</span>
                                                </td>
                                                <td width="33%" style="background: rgba(255,255,255,0.15); border-radius: 6px; padding: 8px; text-align: center;">
                                                    <span style="color: #ffffff; font-size: 18px; font-weight: 700;">{summary.total_stocks}</span>
                                                    <span style="display: block; color: rgba(255,255,255,0.7); font-size: 10px;">Total Holdings</span>
                                                </td>
                                            </tr>
                                        </table>

                                        <!-- Today's Change -->
                                        <table role="presentation" width="100%" style="margin-top: 10px;">
                                            <tr>
                                                <td style="text-align: center;">
                                                    <span style="color: rgba(255,255,255,0.7); font-size: 11px;">Today's Change: </span>
                                                    <span style="color: {day_color}; font-size: 13px; font-weight: 700;">{"▲" if summary.day_change >= 0 else "▼"} {day_sign}₹{abs(summary.day_change):,.0f} ({day_sign}{summary.day_change_pct:.2f}%)</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>"""
    
    def _build_action_alerts(self, insights: PortfolioInsights) -> str:
        """Build action alerts section (BUY/EXIT/BOOK PROFIT)."""
        alerts = []
        
        # BUY recommendation
        if insights.aggressive_buy_stocks:
            top_buy = insights.aggressive_buy_stocks[0]
            alerts.append(f"""
                                <tr>
                                    <td>
                                        <table role="presentation" width="100%" style="background: #dcfce7; border: 2px solid #22c55e; border-radius: 8px;">
                                            <tr>
                                                <td style="padding: 12px;">
                                                    <span style="display: inline-block; background: #22c55e; color: white; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 800;">✅ BUY</span>
                                                    <span style="color: #166534; font-size: 14px; font-weight: 700; margin-left: 8px;">{top_buy.symbol} @ ₹{top_buy.current_price:,.0f}</span>
                                                    <span style="color: #15803d; font-size: 12px;"> — {top_buy.pnl_pct:+.0f}% • {top_buy.reasons[0] if top_buy.reasons else "Strong fundamentals"}</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>""")
        
        # ALSO BUY
        if insights.buy_on_dip_stocks:
            dip_stocks = [f"{h.symbol} ({h.pnl_pct:+.0f}%)" for h in insights.buy_on_dip_stocks[:4]]
            alerts.append(f"""
                                <tr>
                                    <td>
                                        <table role="presentation" width="100%" style="background: #dbeafe; border-radius: 8px;">
                                            <tr>
                                                <td style="padding: 10px 12px;">
                                                    <span style="color: #1d4ed8; font-size: 11px; font-weight: 700;">📥 ALSO BUY ON DIP:</span>
                                                    <span style="color: #1e40af; font-size: 12px;"> {" • ".join(dip_stocks)}</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>""")
        
        # EXIT
        if insights.exit_stocks:
            exit_stocks = [f"{h.symbol} ({h.pnl_pct:+.0f}%)" for h in insights.exit_stocks[:3]]
            alerts.append(f"""
                                <tr>
                                    <td>
                                        <table role="presentation" width="100%" style="background: #fef2f2; border: 2px solid #ef4444; border-radius: 8px;">
                                            <tr>
                                                <td style="padding: 10px 12px;">
                                                    <span style="display: inline-block; background: #ef4444; color: white; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 800;">🚨 EXIT</span>
                                                    <span style="color: #991b1b; font-size: 12px; margin-left: 8px;">{" • ".join(exit_stocks)} — Book loss, weak fundamentals</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>""")
        
        # BOOK PROFIT
        if insights.reduce_stocks:
            profit_stocks = [f"{h.symbol} ({h.pnl_pct:+.0f}%)" for h in insights.reduce_stocks[:4]]
            alerts.append(f"""
                                <tr>
                                    <td>
                                        <table role="presentation" width="100%" style="background: #fef3c7; border-radius: 8px;">
                                            <tr>
                                                <td style="padding: 10px 12px;">
                                                    <span style="color: #92400e; font-size: 11px; font-weight: 700;">💰 BOOK PROFIT:</span>
                                                    <span style="color: #78350f; font-size: 12px;"> {" • ".join(profit_stocks)}</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>""")
        
        if not alerts:
            return ""
        
        return f"""
                    <!-- 🚨 ACTION ALERTS -->
                    <tr>
                        <td style="padding: 0 16px 12px 16px;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="6">
                                {"".join(alerts)}
                            </table>
                        </td>
                    </tr>"""
    
    def _build_holdings_predictions(self, insights: PortfolioInsights) -> str:
        """Build top 5 holdings predictions."""
        predictions = insights.predictions[:5] if insights.predictions else []
        if not predictions:
            return ""
        
        rows = ""
        for h in predictions:
            if h.predicted_direction == "UP":
                arrow = "▲"
                color = "#22c55e"
                bg = "#22c55e"
                label = "CONF"
            elif h.predicted_direction == "DOWN":
                arrow = "▼"
                color = "#ef4444"
                bg = "#ef4444"
                label = "CONF"
            else:
                arrow = "●"
                color = "#f59e0b"
                bg = "#f59e0b"
                label = "HOLD"
            
            rows += f"""
                                            <tr>
                                                <td style="padding: 8px 0; border-bottom: 1px solid #1e293b;">
                                                    <table role="presentation" width="100%">
                                                        <tr>
                                                            <td width="8%" style="text-align: center;"><span style="color: {color}; font-size: 16px;">{arrow}</span></td>
                                                            <td width="28%"><span style="color: #ffffff; font-size: 14px; font-weight: 700;">{h.symbol}</span></td>
                                                            <td width="24%"><span style="display: inline-block; background: {bg}; color: #ffffff; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 600;">{h.predicted_confidence:.0f}% {label}</span></td>
                                                            <td><span style="color: #94a3b8; font-size: 11px;">{h.prediction_reason[:25]}</span></td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>"""
        
        return f"""
                    <!-- 🎯 TOP 5 STOCK PREDICTIONS (Your Holdings) -->
                    <tr>
                        <td style="padding: 0 16px 12px 16px;">
                            <table role="presentation" width="100%" style="background: #0f172a; border-radius: 10px;">
                                <tr>
                                    <td style="padding: 14px;">
                                        <span style="display: block; color: #ffffff; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;">🎯 Top 5 Stock Predictions (Your Holdings)</span>
                                        
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                            {rows}
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>"""
    
    def _build_gainers_losers(self, insights: PortfolioInsights) -> str:
        """Build gainers/losers side by side."""
        # Sort holdings by P&L
        sorted_holdings = sorted(insights.holdings, key=lambda h: h.pnl_pct, reverse=True)
        top_gainers = sorted_holdings[:4]
        top_losers = sorted_holdings[-4:][::-1]  # Reverse to get worst first
        
        gainers_rows = ""
        for h in top_gainers:
            gainers_rows += f"""<tr><td style="padding: 6px 10px; border-bottom: 1px solid #a7f3d0;"><span style="color: #166534; font-size: 12px;">{h.symbol}</span></td><td style="text-align: right; padding: 6px 10px; border-bottom: 1px solid #a7f3d0;"><span style="color: #166534; font-size: 12px; font-weight: 700;">{h.pnl_pct:+.0f}%</span></td></tr>"""
        
        losers_rows = ""
        for h in top_losers:
            losers_rows += f"""<tr><td style="padding: 6px 10px; border-bottom: 1px solid #fecaca;"><span style="color: #991b1b; font-size: 12px;">{h.symbol}</span></td><td style="text-align: right; padding: 6px 10px; border-bottom: 1px solid #fecaca;"><span style="color: #dc2626; font-size: 12px; font-weight: 700;">{h.pnl_pct:+.0f}%</span></td></tr>"""
        
        return f"""
                    <!-- 🏆 Your Top Gainers / Losers -->
                    <tr>
                        <td style="padding: 0 16px 12px 16px;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="8">
                                <tr>
                                    <td width="48%" style="vertical-align: top;">
                                        <span style="display: block; font-size: 10px; font-weight: 700; color: #059669; text-transform: uppercase; margin-bottom: 6px;">🏆 Your Top Gainers</span>
                                        <table role="presentation" width="100%" style="background: #ecfdf5; border-radius: 8px;">
                                            {gainers_rows}
                                        </table>
                                    </td>
                                    <td width="48%" style="vertical-align: top;">
                                        <span style="display: block; font-size: 10px; font-weight: 700; color: #dc2626; text-transform: uppercase; margin-bottom: 6px;">📉 Your Top Losers</span>
                                        <table role="presentation" width="100%" style="background: #fef2f2; border-radius: 8px;">
                                            {losers_rows}
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>"""
    
    def _build_risk_alerts(self, insights: PortfolioInsights) -> str:
        """Build risk alerts section."""
        risk_items = []
        
        # Add exit stocks as risks
        for h in insights.exit_stocks[:3]:
            reason = h.reasons[0] if h.reasons else "Weak fundamentals"
            risk_items.append(f"<strong>{h.symbol}:</strong> {reason}")
        
        if not risk_items:
            return ""
        
        alerts = "<br>• ".join(risk_items)
        
        return f"""
                    <!-- ⚠️ Risk Alerts -->
                    <tr>
                        <td style="padding: 0 16px 12px 16px;">
                            <table role="presentation" width="100%" style="background: #fef2f2; border-left: 4px solid #ef4444; border-radius: 8px;">
                                <tr>
                                    <td style="padding: 12px;">
                                        <span style="display: block; font-size: 11px; font-weight: 700; color: #991b1b; text-transform: uppercase; margin-bottom: 6px;">⚠️ Risk Alerts</span>
                                        <span style="display: block; color: #7f1d1d; font-size: 12px; line-height: 1.6;">
                                            • {alerts}
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>"""
    
    def _build_strategy_section(self, insights: PortfolioInsights) -> str:
        """Build strategy note section."""
        # Build do/don't recommendations
        do_stocks = [h.symbol for h in insights.aggressive_buy_stocks[:3]]
        dont_stocks = [h.symbol for h in insights.exit_stocks[:3]]
        
        do_text = f"Average {', '.join(do_stocks)} on dips" if do_stocks else "Focus on quality stocks"
        dont_text = f"Average {', '.join(dont_stocks)} — book loss" if dont_stocks else "Avoid weak fundamentals"
        
        return f"""
                    <!-- 💡 Strategy Note -->
                    <tr>
                        <td style="padding: 0 16px 16px 16px;">
                            <table role="presentation" width="100%" style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border-radius: 8px;">
                                <tr>
                                    <td style="padding: 14px;">
                                        <span style="display: block; font-size: 11px; font-weight: 700; color: #92400e; text-transform: uppercase; letter-spacing: 1px;">💡 Strategy Note</span>
                                        <p style="margin: 8px 0 0 0; color: #78350f; font-size: 13px; line-height: 1.6;">
                                            {insights.market_outlook}<br><br>
                                            ✅ <strong>Do:</strong> {do_text}<br>
                                            ❌ <strong>Don't:</strong> {dont_text}<br>
                                            💰 <strong>Fresh capital:</strong> {insights.strategy_notes}
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>"""
    
    def _build_footer(self, insights: PortfolioInsights) -> str:
        """Build email footer."""
        profit_loss_url = settings.dashboard_url.rstrip('/') + "/profit-loss.html"
        return f"""
                    <!-- CTA Buttons -->
                    <tr>
                        <td style="padding: 0 16px 20px 16px; text-align: center;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="8">
                                <tr>
                                    <td width="50%" style="text-align: right;">
                                        <a href="{settings.dashboard_url}" style="display: inline-block; background: #0f172a; color: #ffffff; padding: 14px 24px; text-decoration: none; font-size: 12px; font-weight: 700; border-radius: 8px;">
                                            📊 Dashboard →
                                        </a>
                                    </td>
                                    <td width="50%" style="text-align: left;">
                                        <a href="{profit_loss_url}" style="display: inline-block; background: linear-gradient(135deg, #059669 0%, #10b981 100%); color: #ffffff; padding: 14px 24px; text-decoration: none; font-size: 12px; font-weight: 700; border-radius: 8px;">
                                            💰 P&L Report →
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 16px; background: #f1f5f9; text-align: center; border-top: 1px solid #e2e8f0;">
                            <p style="margin: 0; color: #64748b; font-size: 10px;">
                                NSE • Yahoo Finance • MoneyControl • Economic Times
                            </p>
                            <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 9px;">
                                For informational purposes only. DYOR.
                            </p>
                        </td>
                    </tr>"""
    
    def generate_text(self, insights: PortfolioInsights) -> str:
        """Generate plain text email content."""
        summary = insights.summary
        
        lines = [
            "=" * 70,
            "PORTFOLIO ANALYSIS AND RECOMMENDATIONS",
            f"Date: {insights.date}",
            "=" * 70,
            "",
            "PORTFOLIO SUMMARY",
            "-" * 70,
            f"Total Investment:    ₹{summary.total_investment:,.0f}",
            f"Current Value:       ₹{summary.current_value:,.0f}",
            f"Total P&L:           ₹{summary.total_pnl:,.0f} ({summary.total_pnl_pct:+.2f}%)",
            f"Day Change:          ₹{summary.day_change:,.0f} ({summary.day_change_pct:+.2f}%)",
            "",
            f"Total Stocks:        {summary.total_stocks}",
            f"Profitable:          {summary.profitable_stocks}",
            f"Loss Making:         {summary.loss_making_stocks}",
            "",
        ]
        
        # Risk flags
        if summary.risk_flags.get_flags():
            lines.extend([
                "RISK FLAGS",
                "-" * 70,
            ])
            for flag in summary.risk_flags.get_flags():
                lines.append(f"  {flag}")
            lines.append("")
        
        # Sector allocation
        lines.extend([
            "SECTOR ALLOCATION",
            "-" * 70,
            f"{'Sector':<25} {'Value':>15} {'Weight':>10} {'P&L':>12}",
            "-" * 70,
        ])
        for sector in summary.sector_allocation[:5]:
            lines.append(
                f"{sector.sector[:25]:<25} ₹{sector.value:>13,.0f} {sector.weight_pct:>9.1f}% "
                f"{sector.pnl_pct:>+10.1f}%"
            )
        lines.append("")
        
        # Top 20 predictions
        if insights.predictions:
            lines.extend([
                "TOP 20 STOCK MOVEMENT PREDICTIONS",
                "-" * 70,
                f"{'#':<3} {'Symbol':<12} {'Direction':<10} {'Confidence':>10} {'Reason':<35}",
                "-" * 70,
            ])
            for i, h in enumerate(insights.predictions[:20], 1):
                arrow = "▲" if h.predicted_direction == "UP" else "▼" if h.predicted_direction == "DOWN" else "●"
                lines.append(
                    f"{i:<3} {h.symbol:<12} {arrow} {h.predicted_direction:<8} {h.predicted_confidence:>9.0f}% "
                    f"{h.prediction_reason[:35]}"
                )
            lines.append("")
        
        # Portfolio news
        if insights.portfolio_news:
            lines.extend([
                "RELEVANT NEWS FOR YOUR PORTFOLIO",
                "-" * 70,
            ])
            for item in insights.portfolio_news[:10]:
                sentiment = "+" if item.sentiment == "positive" else "-" if item.sentiment == "negative" else "•"
                lines.append(f"  [{sentiment}] {item.headline[:65]}...")
                lines.append(f"      Source: {item.source}")
            lines.append("")
        
        # Decline summary
        lines.extend(self._generate_decline_text(insights.decline_summary))
        
        # Top 10 detailed buy recommendations
        lines.extend(self._generate_detailed_recommendations_text(insights.detailed_buy_recommendations))
        
        # Buy/Hold/Sell signals
        lines.extend([
            "=" * 70,
            "BUY / HOLD / SELL SIGNALS",
            "=" * 70,
            "",
        ])
        
        # Aggressive Buy
        if insights.aggressive_buy_stocks:
            lines.extend([
                "🟢 AGGRESSIVE BUY (Average on Dips)",
                "-" * 70,
            ])
            for h in insights.aggressive_buy_stocks[:5]:
                lines.append(
                    f"  {h.symbol:<12} | Price: ₹{h.current_price:,.2f} | P&L: {h.pnl_pct:+.1f}% | "
                    f"Score: {h.fundamental_score:.0f}/100"
                )
                for reason in h.reasons[:2]:
                    lines.append(f"    • {reason}")
            lines.append("")
        
        # Buy on Dip
        if insights.buy_on_dip_stocks:
            lines.extend([
                "🔵 BUY ON DIP",
                "-" * 70,
            ])
            for h in insights.buy_on_dip_stocks[:5]:
                lines.append(
                    f"  {h.symbol:<12} | Price: ₹{h.current_price:,.2f} | P&L: {h.pnl_pct:+.1f}%"
                )
            lines.append("")
        
        # Hold
        if insights.hold_stocks:
            lines.extend([
                "⚪ HOLD",
                "-" * 70,
            ])
            hold_symbols = [h.symbol for h in insights.hold_stocks[:10]]
            lines.append(f"  {', '.join(hold_symbols)}")
            lines.append("")
        
        # Reduce
        if insights.reduce_stocks:
            lines.extend([
                "🟡 REDUCE (Book Partial Profits)",
                "-" * 70,
            ])
            for h in insights.reduce_stocks[:5]:
                lines.append(
                    f"  {h.symbol:<12} | Price: ₹{h.current_price:,.2f} | P&L: {h.pnl_pct:+.1f}%"
                )
            lines.append("")
        
        # Exit
        if insights.exit_stocks:
            lines.extend([
                "🔴 EXIT (Weak Fundamentals)",
                "-" * 70,
            ])
            for h in insights.exit_stocks:
                lines.append(
                    f"  {h.symbol:<12} | Price: ₹{h.current_price:,.2f} | P&L: {h.pnl_pct:+.1f}% | "
                    f"Score: {h.fundamental_score:.0f}/100"
                )
                for reason in h.reasons[:2]:
                    lines.append(f"    ⚠️ {reason}")
            lines.append("")
        
        # Strategy notes
        lines.extend([
            "=" * 70,
            "STRATEGY NOTES",
            "=" * 70,
            "",
            insights.market_outlook,
            "",
            insights.strategy_notes,
            "",
            "=" * 70,
            "",
            f"📈 VIEW FULL MARKET DASHBOARD: {settings.dashboard_url}",
            f"💰 PROFIT & LOSS REPORT: {settings.dashboard_url.rstrip('/')}/profit-loss.html",
            "",
            "=" * 70,
        ])
        
        return "\n".join(lines)
    
    def _build_header(self, insights: PortfolioInsights) -> str:
        """Build portfolio header section."""
        summary = insights.summary
        
        pnl_color = "#28a745" if summary.total_pnl >= 0 else "#dc3545"
        pnl_sign = "+" if summary.total_pnl >= 0 else ""
        day_color = "#28a745" if summary.day_change >= 0 else "#dc3545"
        day_sign = "+" if summary.day_change >= 0 else ""
        
        return f"""
        <div class="header">
            <h1>📊 Portfolio Analysis and Recommendations</h1>
            <p class="date">{insights.date}</p>
            <a href="{settings.dashboard_url}" target="_blank" class="dashboard-btn">🌐 View Live Dashboard</a>
        </div>
        
        <div class="summary-grid">
            <div class="summary-card">
                <div class="card-label">Total Investment</div>
                <div class="card-value">₹{summary.total_investment:,.0f}</div>
            </div>
            <div class="summary-card">
                <div class="card-label">Current Value</div>
                <div class="card-value">₹{summary.current_value:,.0f}</div>
            </div>
            <div class="summary-card">
                <div class="card-label">Total P&L</div>
                <div class="card-value" style="color: {pnl_color};">
                    {pnl_sign}₹{abs(summary.total_pnl):,.0f}
                    <span class="pct">({pnl_sign}{summary.total_pnl_pct:.2f}%)</span>
                </div>
            </div>
            <div class="summary-card">
                <div class="card-label">Day Change</div>
                <div class="card-value" style="color: {day_color};">
                    {day_sign}₹{abs(summary.day_change):,.0f}
                    <span class="pct">({day_sign}{summary.day_change_pct:.2f}%)</span>
                </div>
            </div>
        </div>
        
        <div class="stats-row">
            <div class="stat">
                <span class="stat-value">{summary.total_stocks}</span>
                <span class="stat-label">Total Stocks</span>
            </div>
            <div class="stat">
                <span class="stat-value" style="color: #28a745;">{summary.profitable_stocks}</span>
                <span class="stat-label">Profitable</span>
            </div>
            <div class="stat">
                <span class="stat-value" style="color: #dc3545;">{summary.loss_making_stocks}</span>
                <span class="stat-label">Loss Making</span>
            </div>
            <div class="stat">
                <span class="stat-value">{summary.overall_risk_level.value}</span>
                <span class="stat-label">Risk Level</span>
            </div>
        </div>
        """
    
    def _build_risk_flags(self, summary) -> str:
        """Build risk flags section."""
        flags = summary.risk_flags.get_flags()
        if not flags:
            return ""
        
        flags_html = "".join([f'<div class="risk-flag">{flag}</div>' for flag in flags])
        
        return f"""
        <div class="section risk-section">
            <h2>⚠️ Risk Flags</h2>
            <div class="risk-flags">
                {flags_html}
            </div>
        </div>
        """
    
    def _build_sector_allocation(self, summary) -> str:
        """Build sector allocation section."""
        rows = ""
        for sector in summary.sector_allocation[:6]:
            pnl_color = "#28a745" if sector.pnl_pct >= 0 else "#dc3545"
            pnl_sign = "+" if sector.pnl_pct >= 0 else ""
            
            rows += f"""
            <tr>
                <td><strong>{sector.sector}</strong></td>
                <td>₹{sector.value:,.0f}</td>
                <td>{sector.weight_pct:.1f}%</td>
                <td style="color: {pnl_color};">{pnl_sign}{sector.pnl_pct:.1f}%</td>
                <td>{sector.stock_count}</td>
            </tr>
            """
        
        return f"""
        <div class="section">
            <h2>📈 Sector Allocation</h2>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Sector</th>
                        <th>Value</th>
                        <th>Weight</th>
                        <th>P&L</th>
                        <th>Stocks</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        """
    
    def _build_predictions(self, predictions: list[HoldingAnalysis]) -> str:
        """Build predictions section."""
        if not predictions:
            return ""
        
        rows = ""
        for i, h in enumerate(predictions[:20], 1):
            direction_color = "#28a745" if h.predicted_direction == "UP" else "#dc3545" if h.predicted_direction == "DOWN" else "#6c757d"
            arrow = "▲" if h.predicted_direction == "UP" else "▼" if h.predicted_direction == "DOWN" else "●"
            
            rows += f"""
            <tr>
                <td>{i}</td>
                <td><strong>{h.symbol}</strong></td>
                <td>₹{h.current_price:,.2f}</td>
                <td style="color: {direction_color}; font-weight: bold;">{arrow} {h.predicted_direction}</td>
                <td>{h.predicted_confidence:.0f}%</td>
                <td><small>{h.prediction_reason}</small></td>
            </tr>
            """
        
        return f"""
        <div class="section">
            <h2>🎯 Top 20 Stock Movement Predictions</h2>
            <p class="section-subtitle">Predictions for your portfolio stocks based on technical and fundamental analysis</p>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Stock</th>
                        <th>Price</th>
                        <th>Direction</th>
                        <th>Confidence</th>
                        <th>Reason</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        """
    
    def _build_portfolio_news(self, news_items) -> str:
        """Build portfolio news section."""
        if not news_items:
            return ""
        
        items_html = ""
        for item in news_items[:10]:
            sentiment_color = {"positive": "#28a745", "negative": "#dc3545"}.get(item.sentiment, "#6c757d")
            sentiment_icon = {"positive": "▲", "negative": "▼"}.get(item.sentiment, "●")
            
            stocks_badges = ""
            for stock in item.stocks_mentioned[:3]:
                stocks_badges += f'<span class="stock-badge">{stock}</span>'
            
            items_html += f"""
            <div class="news-item">
                <span class="sentiment" style="color: {sentiment_color};">{sentiment_icon}</span>
                <div class="news-content">
                    <a href="{item.url}" target="_blank">{item.headline}</a>
                    <div class="news-meta">
                        <span class="source">{item.source}</span>
                        {stocks_badges}
                    </div>
                </div>
            </div>
            """
        
        return f"""
        <div class="section">
            <h2>📰 News Relevant to Your Portfolio</h2>
            <div class="news-list">
                {items_html}
            </div>
        </div>
        """
    
    def _build_signals_section(self, insights: PortfolioInsights) -> str:
        """Build buy/hold/sell signals section."""
        
        # Aggressive Buy section
        aggressive_html = self._build_signal_group(
            "🟢 AGGRESSIVE BUY",
            "Strong fundamentals - Average aggressively on dips",
            insights.aggressive_buy_stocks,
            "#28a745",
        )
        
        # Buy on Dip section
        buy_dip_html = self._build_signal_group(
            "🔵 BUY ON DIP",
            "Good stocks - Accumulate on weakness",
            insights.buy_on_dip_stocks,
            "#007bff",
        )
        
        # Hold section
        hold_html = ""
        if insights.hold_stocks:
            hold_symbols = ", ".join([h.symbol for h in insights.hold_stocks[:15]])
            more = f" (+{len(insights.hold_stocks) - 15} more)" if len(insights.hold_stocks) > 15 else ""
            hold_html = f"""
            <div class="signal-group">
                <h3 style="color: #6c757d;">⚪ HOLD</h3>
                <p class="signal-desc">Maintain current positions</p>
                <p><strong>{hold_symbols}{more}</strong></p>
            </div>
            """
        
        # Reduce section
        reduce_html = self._build_signal_group(
            "🟡 REDUCE",
            "Consider booking partial profits",
            insights.reduce_stocks,
            "#ffc107",
            limit=5,
        )
        
        # Exit section
        exit_html = self._build_signal_group(
            "🔴 EXIT",
            "Weak fundamentals - Exit during market recovery",
            insights.exit_stocks,
            "#dc3545",
        )
        
        return f"""
        <div class="section signals-section">
            <h2>📋 Buy / Hold / Sell Signals</h2>
            <p class="section-subtitle">Long-term investment recommendations based on fundamental analysis</p>
            
            {aggressive_html}
            {buy_dip_html}
            {hold_html}
            {reduce_html}
            {exit_html}
        </div>
        """
    
    def _build_signal_group(self, title: str, desc: str, holdings: list, color: str, limit: int = 8) -> str:
        """Build a signal group section."""
        if not holdings:
            return ""
        
        rows = ""
        for h in holdings[:limit]:
            pnl_color = "#28a745" if h.pnl_pct >= 0 else "#dc3545"
            reasons_html = " | ".join(h.reasons[:2])
            
            rows += f"""
            <tr>
                <td><strong>{h.symbol}</strong><br><small>{h.company_name[:20]}...</small></td>
                <td>₹{h.current_price:,.2f}</td>
                <td style="color: {pnl_color};">{h.pnl_pct:+.1f}%</td>
                <td>{h.fundamental_score:.0f}/100</td>
                <td>{h.risk_level.value}</td>
                <td><small>{reasons_html}</small></td>
            </tr>
            """
        
        return f"""
        <div class="signal-group">
            <h3 style="color: {color};">{title}</h3>
            <p class="signal-desc">{desc}</p>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Stock</th>
                        <th>Price</th>
                        <th>P&L</th>
                        <th>Score</th>
                        <th>Risk</th>
                        <th>Reasons</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        """
    
    def _build_strategy_section(self, insights: PortfolioInsights) -> str:
        """Build strategy section."""
        return f"""
        <div class="section strategy-section">
            <h2>📋 Strategy & Market Outlook</h2>
            <div class="outlook-box">
                <h4>Market Outlook</h4>
                <p>{insights.market_outlook}</p>
            </div>
            <div class="strategy-box">
                <h4>Your Portfolio Strategy</h4>
                <p>{insights.strategy_notes}</p>
            </div>
        </div>
        """
    
    def _get_css(self) -> str:
        """Get CSS styles."""
        return """
        <style>
            * { box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                background: #f5f5f5;
                margin: 0;
                padding: 20px;
            }
            .container {
                max-width: 900px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #1a237e 0%, #3949ab 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .header h1 {
                margin: 0;
                font-size: 24px;
            }
            .date {
                margin: 10px 0 0 0;
                opacity: 0.9;
            }
            .dashboard-btn {
                display: inline-block;
                margin-top: 15px;
                padding: 12px 24px;
                background: #fff;
                color: #1a237e;
                text-decoration: none;
                border-radius: 25px;
                font-weight: 600;
                font-size: 14px;
                transition: all 0.3s ease;
            }
            .dashboard-btn:hover {
                background: #e8eaf6;
                transform: scale(1.05);
            }
            .summary-grid {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 15px;
                padding: 20px;
                background: #f8f9fa;
            }
            .summary-card {
                background: white;
                padding: 15px;
                border-radius: 8px;
                text-align: center;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }
            .card-label {
                font-size: 12px;
                color: #666;
                text-transform: uppercase;
            }
            .card-value {
                font-size: 18px;
                font-weight: bold;
                margin-top: 5px;
            }
            .card-value .pct {
                font-size: 12px;
                font-weight: normal;
            }
            .stats-row {
                display: flex;
                justify-content: space-around;
                padding: 15px 20px;
                border-bottom: 1px solid #eee;
            }
            .stat {
                text-align: center;
            }
            .stat-value {
                font-size: 24px;
                font-weight: bold;
                display: block;
            }
            .stat-label {
                font-size: 12px;
                color: #666;
            }
            .section {
                padding: 20px;
                border-bottom: 1px solid #eee;
            }
            .section h2 {
                margin: 0 0 15px 0;
                font-size: 18px;
                color: #333;
            }
            .section-subtitle {
                margin: -10px 0 15px 0;
                color: #666;
                font-size: 13px;
            }
            .data-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 13px;
            }
            .data-table th, .data-table td {
                padding: 10px 8px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }
            .data-table th {
                background: #f8f9fa;
                font-weight: 600;
                font-size: 11px;
                text-transform: uppercase;
                color: #666;
            }
            .risk-section {
                background: #fff3cd;
            }
            .risk-flags {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
            }
            .risk-flag {
                background: #ffc107;
                color: #856404;
                padding: 8px 12px;
                border-radius: 4px;
                font-size: 13px;
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
            .news-item .sentiment {
                font-size: 16px;
            }
            .news-item a {
                color: #1a237e;
                text-decoration: none;
                font-weight: 500;
            }
            .news-item a:hover {
                text-decoration: underline;
            }
            .news-meta {
                margin-top: 5px;
                font-size: 12px;
                color: #666;
            }
            .stock-badge {
                background: #e3f2fd;
                color: #1565c0;
                padding: 2px 6px;
                border-radius: 3px;
                margin-left: 5px;
                font-size: 11px;
            }
            .signal-group {
                margin-bottom: 25px;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 8px;
            }
            .signal-group h3 {
                margin: 0 0 5px 0;
                font-size: 16px;
            }
            .signal-desc {
                margin: 0 0 15px 0;
                font-size: 13px;
                color: #666;
            }
            .strategy-section {
                background: #e8eaf6;
            }
            .outlook-box, .strategy-box {
                background: white;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 15px;
            }
            .outlook-box h4, .strategy-box h4 {
                margin: 0 0 10px 0;
                color: #1a237e;
            }
            .footer {
                padding: 20px;
                text-align: center;
                background: #f8f9fa;
                font-size: 12px;
                color: #666;
            }
            .decline-section {
                background: #fff8e1;
            }
            .decline-category {
                margin-bottom: 15px;
                padding: 12px;
                background: white;
                border-radius: 6px;
            }
            .decline-category h4 {
                margin: 0 0 8px 0;
                font-size: 14px;
            }
            .decline-stocks {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
            }
            .decline-stock {
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
            }
            .decline-20-30 { background: #fff3cd; color: #856404; }
            .decline-30-40 { background: #ffe0b2; color: #e65100; }
            .decline-40-plus { background: #ffcdd2; color: #c62828; }
            .rec-card {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                margin-bottom: 20px;
                overflow: hidden;
            }
            .rec-header {
                background: linear-gradient(135deg, #1b5e20 0%, #2e7d32 100%);
                color: white;
                padding: 15px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .rec-header h4 {
                margin: 0;
                font-size: 16px;
            }
            .rec-signal {
                background: rgba(255,255,255,0.2);
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
            }
            .rec-body {
                padding: 15px;
            }
            .rec-metrics {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 10px;
                margin-bottom: 15px;
            }
            .rec-metric {
                text-align: center;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 6px;
            }
            .rec-metric-value {
                font-size: 16px;
                font-weight: bold;
                color: #1b5e20;
            }
            .rec-metric-label {
                font-size: 10px;
                color: #666;
                text-transform: uppercase;
            }
            .rec-reasons {
                list-style: none;
                padding: 0;
                margin: 10px 0;
            }
            .rec-reasons li {
                padding: 6px 0;
                border-bottom: 1px solid #eee;
                font-size: 13px;
            }
            .rec-news {
                background: #e3f2fd;
                padding: 10px;
                border-radius: 6px;
                margin-top: 10px;
            }
            .rec-news h5 {
                margin: 0 0 8px 0;
                font-size: 12px;
                color: #1565c0;
            }
            .rec-news ul {
                margin: 0;
                padding-left: 20px;
                font-size: 12px;
            }
            @media (max-width: 600px) {
                .summary-grid {
                    grid-template-columns: repeat(2, 1fr);
                }
                .stats-row {
                    flex-wrap: wrap;
                }
                .stat {
                    width: 50%;
                    margin-bottom: 10px;
                }
                .rec-metrics {
                    grid-template-columns: repeat(2, 1fr);
                }
            }
        </style>
        """
    
    def _build_decline_summary(self, decline_summary: DeclineSummary) -> str:
        """Build decline summary section showing stocks fallen by 20%, 30%, 40%+."""
        
        def build_decline_category(title: str, category, date_label: str) -> str:
            has_stocks = (category.down_20_30 or category.down_30_40 or category.down_40_plus)
            if not has_stocks:
                return ""
            
            down_20_html = ""
            if category.down_20_30:
                stocks = " ".join([f'<span class="decline-stock decline-20-30">{s}</span>' for s in category.down_20_30[:5]])
                down_20_html = f'<div><strong>📉 Down 20-30%:</strong> {stocks}</div>'
            
            down_30_html = ""
            if category.down_30_40:
                stocks = " ".join([f'<span class="decline-stock decline-30-40">{s}</span>' for s in category.down_30_40[:5]])
                down_30_html = f'<div style="margin-top:8px;"><strong>📉 Down 30-40%:</strong> {stocks}</div>'
            
            down_40_html = ""
            if category.down_40_plus:
                stocks = " ".join([f'<span class="decline-stock decline-40-plus">{s}</span>' for s in category.down_40_plus[:5]])
                down_40_html = f'<div style="margin-top:8px;"><strong>🔻 Down 40%+:</strong> {stocks}</div>'
            
            return f"""
            <div class="decline-category">
                <h4>📅 {title} ({date_label})</h4>
                {down_20_html}
                {down_30_html}
                {down_40_html}
            </div>
            """
        
        feb28_html = build_decline_category("Since Feb 28, 2026", decline_summary.since_feb28_2026, "~1 month")
        jan1_html = build_decline_category("Since Jan 1, 2026", decline_summary.since_jan1_2026, "YTD")
        year_html = build_decline_category("Since Last Year", decline_summary.since_last_year, "1 Year")
        two_year_html = build_decline_category("Since 2+ Years Ago", decline_summary.since_2_years, "Long-term")
        
        if not any([feb28_html, jan1_html, year_html, two_year_html]):
            return ""
        
        return f"""
        <div class="section decline-section">
            <h2>📉 Stock Decline Analysis</h2>
            <p class="section-subtitle">Stocks fallen significantly from key dates - potential value opportunities</p>
            {feb28_html}
            {jan1_html}
            {year_html}
            {two_year_html}
        </div>
        """
    
    def _build_detailed_recommendations(self, recommendations: list) -> str:
        """Build top 10 detailed strong buy recommendations."""
        if not recommendations:
            return ""
        
        cards_html = ""
        for i, rec in enumerate(recommendations[:10], 1):
            # Build reasons list
            reasons_html = ""
            for reason in rec.reasons[:6]:
                reasons_html += f"<li>{reason}</li>"
            
            # Build news section
            news_html = ""
            if rec.related_news:
                news_items = "".join([f"<li>{n}</li>" for n in rec.related_news[:3]])
                news_html = f"""
                <div class="rec-news">
                    <h5>📰 Related News</h5>
                    <ul>{news_items}</ul>
                </div>
                """
            
            cards_html += f"""
            <div class="rec-card">
                <div class="rec-header">
                    <div>
                        <h4>#{i} {rec.symbol}</h4>
                        <small>{rec.company_name} | {rec.sector}</small>
                    </div>
                    <span class="rec-signal">{rec.signal}</span>
                </div>
                <div class="rec-body">
                    <div class="rec-metrics">
                        <div class="rec-metric">
                            <div class="rec-metric-value">₹{rec.current_price:,.2f}</div>
                            <div class="rec-metric-label">Current Price</div>
                        </div>
                        <div class="rec-metric">
                            <div class="rec-metric-value">{rec.recommended_qty}</div>
                            <div class="rec-metric-label">Buy Qty</div>
                        </div>
                        <div class="rec-metric">
                            <div class="rec-metric-value">₹{rec.recommended_investment:,.0f}</div>
                            <div class="rec-metric-label">Investment</div>
                        </div>
                        <div class="rec-metric">
                            <div class="rec-metric-value">₹{rec.target_price:,.2f}</div>
                            <div class="rec-metric-label">Target</div>
                        </div>
                        <div class="rec-metric">
                            <div class="rec-metric-value">₹{rec.stop_loss:,.2f}</div>
                            <div class="rec-metric-label">Stop Loss</div>
                        </div>
                        <div class="rec-metric">
                            <div class="rec-metric-value" style="color: #28a745;">{rec.expected_return_pct:+.1f}%</div>
                            <div class="rec-metric-label">Expected Return</div>
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 10px;">
                        <strong>Entry Range:</strong> {rec.entry_price_range} | 
                        <strong>Score:</strong> {rec.fundamental_score:.0f}/100 | 
                        <strong>Confidence:</strong> {rec.overall_confidence:.0f}%
                    </div>
                    
                    <div style="font-size: 12px; color: #666; margin-bottom: 10px;">
                        <strong>Decline:</strong> 
                        From Cost: {rec.decline_from_high:+.1f}% | 
                        Since Feb 28: {rec.decline_from_feb28:+.1f}% | 
                        Since Jan 1: {rec.decline_from_jan1:+.1f}%
                    </div>
                    
                    <h5 style="margin: 15px 0 8px 0; font-size: 13px;">💡 Why Buy This Stock:</h5>
                    <ul class="rec-reasons">
                        {reasons_html}
                    </ul>
                    
                    {news_html}
                </div>
            </div>
            """
        
        return f"""
        <div class="section">
            <h2>🎯 TOP 10 STRONG BUY RECOMMENDATIONS</h2>
            <p class="section-subtitle">Detailed analysis with quantity, reasons, news, FII activity, and more</p>
            {cards_html}
        </div>
        """
    
    def _generate_decline_text(self, decline_summary: DeclineSummary) -> list[str]:
        """Generate text version of decline summary."""
        lines = []
        
        def add_category(title: str, category, lines: list):
            has_stocks = (category.down_20_30 or category.down_30_40 or category.down_40_plus)
            if not has_stocks:
                return
            
            lines.extend([
                "",
                f"{title}",
                "-" * 50,
            ])
            
            if category.down_20_30:
                lines.append(f"  📉 Down 20-30%: {', '.join(category.down_20_30[:5])}")
            if category.down_30_40:
                lines.append(f"  📉 Down 30-40%: {', '.join(category.down_30_40[:5])}")
            if category.down_40_plus:
                lines.append(f"  🔻 Down 40%+: {', '.join(category.down_40_plus[:5])}")
        
        lines.extend([
            "=" * 70,
            "STOCK DECLINE ANALYSIS",
            "=" * 70,
        ])
        
        add_category("Since Feb 28, 2026 (~1 month)", decline_summary.since_feb28_2026, lines)
        add_category("Since Jan 1, 2026 (YTD)", decline_summary.since_jan1_2026, lines)
        add_category("Since Last Year (1 Year)", decline_summary.since_last_year, lines)
        add_category("Since 2+ Years Ago", decline_summary.since_2_years, lines)
        
        lines.append("")
        return lines
    
    def _generate_detailed_recommendations_text(self, recommendations: list) -> list[str]:
        """Generate text version of detailed buy recommendations."""
        lines = [
            "=" * 70,
            "TOP 10 STRONG BUY RECOMMENDATIONS",
            "=" * 70,
            "",
        ]
        
        for i, rec in enumerate(recommendations[:10], 1):
            lines.extend([
                f"{'='*60}",
                f"#{i} {rec.symbol} - {rec.company_name}",
                f"{'='*60}",
                f"Sector: {rec.sector} | Signal: {rec.signal}",
                f"",
                f"PRICE & QUANTITY:",
                f"  Current Price:  ₹{rec.current_price:,.2f}",
                f"  Buy Quantity:   {rec.recommended_qty} shares",
                f"  Investment:     ₹{rec.recommended_investment:,.0f}",
                f"  Entry Range:    {rec.entry_price_range}",
                f"  Target Price:   ₹{rec.target_price:,.2f} ({rec.expected_return_pct:+.1f}%)",
                f"  Stop Loss:      ₹{rec.stop_loss:,.2f}",
                f"",
                f"SCORES:",
                f"  Fundamental:    {rec.fundamental_score:.0f}/100",
                f"  Technical:      {rec.technical_score:.0f}/100",
                f"  Overall:        {rec.overall_confidence:.0f}%",
                f"",
                f"DECLINE METRICS:",
                f"  From Cost:      {rec.decline_from_high:+.1f}%",
                f"  Since Feb 28:   {rec.decline_from_feb28:+.1f}%",
                f"  Since Jan 1:    {rec.decline_from_jan1:+.1f}%",
                f"",
                f"WHY BUY THIS STOCK:",
            ])
            
            for reason in rec.reasons[:6]:
                lines.append(f"  • {reason}")
            
            if rec.related_news:
                lines.extend([
                    f"",
                    f"RELATED NEWS:",
                ])
                for news in rec.related_news[:3]:
                    lines.append(f"  📰 {news}")
            
            lines.append("")
        
        return lines
