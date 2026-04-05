"""
Stock Service.
Main orchestration service that coordinates all components.
"""

import logging
from datetime import datetime
from typing import Optional

from app.config import settings
from app.data.models import DailyReport, StockRecommendation, Signal
from app.data.nse_client import NSEClient
from app.analysis.screener import MarketScreener
from app.analysis.recovery import RecoveryScreener
from app.analysis.portfolio import PortfolioAnalyzer
from app.analysis.market_overview import MarketOverviewFetcher, MarketOverview
from app.analysis.newsletter import NewsletterGenerator, Newsletter
from app.analysis.portfolio_insights import PortfolioInsightsGenerator, PortfolioInsights
from app.analysis.portfolio_email import PortfolioEmailGenerator
from app.notification.emailer import EmailNotifier

logger = logging.getLogger(__name__)


class StockService:
    """Main service for stock screening and analysis."""
    
    def __init__(self):
        """Initialize the stock service."""
        self._nse_client = NSEClient()
        self._screener = MarketScreener()
        self._recovery_screener = RecoveryScreener(
            min_decline_pct=20.0,
            max_decline_pct=50.0,
        )
        self._portfolio_analyzer = PortfolioAnalyzer()
        self._market_overview_fetcher = MarketOverviewFetcher()
        self._newsletter_generator = NewsletterGenerator()
        self._portfolio_insights_generator = PortfolioInsightsGenerator()
        self._portfolio_email_generator = PortfolioEmailGenerator()
        self._email_notifier = EmailNotifier(
            smtp_host=settings.smtp_host,
            smtp_port=settings.smtp_port,
            smtp_user=settings.smtp_user,
            smtp_password=settings.smtp_password,
            from_email=settings.email_from,
            to_emails=settings.email_to,
        )
        
        # Cache last results
        self._last_report: Optional[DailyReport] = None
        self._last_market_overview: Optional[MarketOverview] = None
        self._last_newsletter: Optional[Newsletter] = None
        self._last_portfolio_insights: Optional[PortfolioInsights] = None
    
    def run_daily_scan(self, notify: bool = True) -> DailyReport:
        """
        Run the daily market scan.
        
        Args:
            notify: Send email notification
            
        Returns:
            DailyReport: Results of the scan
        """
        logger.info("Starting daily market scan...")
        
        # Fetch market overview (global indices)
        logger.info("Fetching global market overview...")
        market_overview = self._market_overview_fetcher.get_overview()
        self._last_market_overview = market_overview
        
        # Generate newsletter (news, intelligence, predictions)
        logger.info("Generating market newsletter...")
        newsletter = self._newsletter_generator.generate()
        self._last_newsletter = newsletter
        
        # Fetch all stocks
        stocks = self._nse_client.fetch_all_stocks(include_micro=True)
        
        # Screen for buy/sell signals
        logger.info("Screening for buy/sell signals...")
        buy_signals, sell_signals = self._screener.screen(stocks, top_n=10)
        
        # Screen for recovery candidates
        logger.info("Screening for recovery candidates...")
        recovery_candidates = self._recovery_screener.screen(stocks)[:10]
        
        # Build report
        report = DailyReport(
            date=datetime.now().strftime("%Y-%m-%d"),
            market_status=self._get_market_status(),
            buy_signals=buy_signals,
            sell_signals=sell_signals,
            recovery_candidates=recovery_candidates,
            total_stocks_analyzed=len(stocks),
            strong_buys=len([s for s in buy_signals if s.signal == Signal.STRONG_BUY]),
            strong_sells=len([s for s in sell_signals if s.signal == Signal.STRONG_SELL]),
        )
        
        self._last_report = report
        
        # Generate portfolio insights if holdings file exists
        portfolio_insights = None
        try:
            logger.info("Generating portfolio insights...")
            portfolio_insights = self._portfolio_insights_generator.generate()
            self._last_portfolio_insights = portfolio_insights
            logger.info(f"Portfolio analysis: {len(portfolio_insights.holdings)} holdings, P/L: {portfolio_insights.summary.total_pnl_pct:.2f}%")
        except Exception as e:
            logger.warning(f"Portfolio insights generation failed: {e}")
        
        # Send email notification (includes portfolio analysis at the end)
        if notify:
            self._send_report_email(report, market_overview, newsletter, portfolio_insights)
        
        logger.info(
            f"Scan complete: {len(buy_signals)} buy signals, "
            f"{len(sell_signals)} sell signals, "
            f"{len(recovery_candidates)} recovery candidates"
        )
        
        return report
    
    def analyze_portfolio(self, csv_path: str) -> DailyReport:
        """
        Analyze portfolio from CSV file.
        
        Args:
            csv_path: Path to portfolio CSV
            
        Returns:
            DailyReport: Report with portfolio analysis
        """
        logger.info(f"Analyzing portfolio from {csv_path}...")
        
        holdings = self._portfolio_analyzer.analyze_csv(csv_path)
        
        report = DailyReport(
            date=datetime.now().strftime("%Y-%m-%d"),
            market_status="Portfolio Analysis",
            portfolio_analysis=holdings,
            total_stocks_analyzed=len(holdings),
        )
        
        return report
    
    def get_buy_signals(self, top_n: int = 10) -> list[StockRecommendation]:
        """Get top buy signals."""
        if self._last_report:
            return self._last_report.buy_signals[:top_n]
        
        buy_signals, _ = self._screener.screen(top_n=top_n)
        return buy_signals
    
    def get_sell_signals(self, top_n: int = 10) -> list[StockRecommendation]:
        """Get top sell signals."""
        if self._last_report:
            return self._last_report.sell_signals[:top_n]
        
        _, sell_signals = self._screener.screen(top_n=top_n)
        return sell_signals
    
    def get_last_report(self) -> Optional[DailyReport]:
        """Get the last generated report."""
        return self._last_report
    
    def run_portfolio_analysis(self, notify: bool = True) -> PortfolioInsights:
        """
        Run portfolio analysis and send email.
        
        This is separate from the daily scan and sends an email with:
        - Portfolio summary (value, P/L, allocation, risk flags)
        - Top 20 stock movement predictions for portfolio stocks
        - Relevant news for portfolio stocks
        - Buy/Hold/Sell signals for each holding
        
        Args:
            notify: Send email notification
            
        Returns:
            PortfolioInsights: Complete portfolio analysis
        """
        logger.info("Running portfolio analysis...")
        
        # Generate portfolio insights
        insights = self._portfolio_insights_generator.generate()
        self._last_portfolio_insights = insights
        
        # Send email notification
        if notify:
            self._send_portfolio_email(insights)
        
        logger.info(
            f"Portfolio analysis complete: {len(insights.holdings)} holdings, "
            f"P/L: {insights.summary.total_pnl_pct:.2f}%, "
            f"Aggressive Buy: {len(insights.aggressive_buy_stocks)}, "
            f"Exit: {len(insights.exit_stocks)}"
        )
        
        return insights
    
    def _send_portfolio_email(self, insights: PortfolioInsights) -> bool:
        """Send portfolio analysis email."""
        subject = f"Portfolio Analysis and Recommendations - {insights.date}"
        
        # Build plain text body
        body = self._portfolio_email_generator.generate_text(insights)
        
        # Build HTML body
        html_body = self._portfolio_email_generator.generate_html(insights)
        
        return self._email_notifier.send(subject, body, html_body)
    
    def get_last_portfolio_insights(self) -> Optional[PortfolioInsights]:
        """Get the last generated portfolio insights."""
        return self._last_portfolio_insights
    
    def _get_market_status(self) -> str:
        """Get current market status."""
        try:
            if self._nse_client.is_market_open():
                return "Market Open"
            return "Market Closed"
        except Exception:
            return "Unknown"
    
    def _send_report_email(self, report: DailyReport, market_overview: Optional[MarketOverview] = None, newsletter: Optional[Newsletter] = None, portfolio_insights: Optional[PortfolioInsights] = None) -> bool:
        """Send daily report via email (includes portfolio analysis at the end)."""
        subject = f"Stock Market Daily Recommendation - {report.date}"
        
        # Build plain text body
        body = self._build_text_report(report, market_overview, newsletter, portfolio_insights)
        
        # Build HTML body
        html_body = self._build_html_report(report, market_overview, newsletter, portfolio_insights)
        
        return self._email_notifier.send(subject, body, html_body)
    
    def _build_text_report(self, report: DailyReport, market_overview: Optional[MarketOverview] = None, newsletter: Optional[Newsletter] = None, portfolio_insights: Optional[PortfolioInsights] = None) -> str:
        """Build plain text report with table format."""
        lines = [
            "=" * 70,
            f"STOCK MARKET DAILY RECOMMENDATION - {report.date}",
            "=" * 70,
        ]
        
        # Add newsletter text content if available
        if newsletter:
            lines.append("")
            lines.append(newsletter.text_content)
        
        # Add market overview section
        if market_overview:
            lines.extend([
                "",
                "GLOBAL MARKET OVERVIEW",
                "-" * 70,
            ])
            if market_overview.dow_jones:
                dj = market_overview.dow_jones
                arrow = "▲" if dj.is_up else "▼"
                lines.append(f"Dow Jones: {dj.last_close:,.2f} {arrow} {abs(dj.change_pct):.2f}%")
            if market_overview.nasdaq:
                nq = market_overview.nasdaq
                arrow = "▲" if nq.is_up else "▼"
                lines.append(f"NASDAQ:    {nq.last_close:,.2f} {arrow} {abs(nq.change_pct):.2f}%")
            if market_overview.gift_nifty:
                gn = market_overview.gift_nifty
                arrow = "▲" if gn.is_up else "▼"
                lines.append(f"GIFT Nifty: {gn.last_close:,.2f} {arrow} {abs(gn.change_pct):.2f}%")
            if market_overview.usd_inr:
                ui = market_overview.usd_inr
                arrow = "▲" if ui.is_up else "▼"
                lines.append(f"USD/INR:   ₹{ui.last_close:.2f} {arrow} {abs(ui.change_pct):.2f}%")
            lines.append("-" * 70)
            if market_overview.sensex:
                sx = market_overview.sensex
                arrow = "▲" if sx.is_up else "▼"
                lines.append(f"Sensex:    {sx.last_close:,.2f} {arrow} {abs(sx.change_pct):.2f}%")
            if market_overview.nifty:
                nf = market_overview.nifty
                arrow = "▲" if nf.is_up else "▼"
                lines.append(f"Nifty 50:  {nf.last_close:,.2f} {arrow} {abs(nf.change_pct):.2f}%")
            lines.extend([
                "-" * 70,
                f"MARKET OUTLOOK: {market_overview.market_outlook}",
                f"Reason: {market_overview.outlook_reason}",
                "=" * 70,
            ])
        
        lines.extend([
            f"Market Status: {report.market_status}",
            f"Stocks Analyzed: {report.total_stocks_analyzed}",
            "",
            "-" * 70,
            "TOP 10 BUY RECOMMENDATIONS",
            "-" * 70,
            f"{'#':<3} {'Symbol':<12} {'Price':>10} {'Target':>10} {'Signal':<12} {'Confidence':>10}",
            "-" * 70,
        ])
        
        for i, rec in enumerate(report.buy_signals, 1):
            lines.append(
                f"{i:<3} {rec.symbol:<12} {rec.current_price:>10.2f} {rec.target_price:>10.2f} "
                f"{rec.signal.value:<12} {rec.confidence:>9.0f}%"
            )
            for reason in rec.reasons[:3]:
                lines.append(f"    • {reason}")
        
        lines.extend([
            "",
            "-" * 70,
            "TOP 10 SELL RECOMMENDATIONS",
            "-" * 70,
            f"{'#':<3} {'Symbol':<12} {'Price':>10} {'Target':>10} {'Signal':<12} {'Confidence':>10}",
            "-" * 70,
        ])
        
        for i, rec in enumerate(report.sell_signals, 1):
            lines.append(
                f"{i:<3} {rec.symbol:<12} {rec.current_price:>10.2f} {rec.target_price:>10.2f} "
                f"{rec.signal.value:<12} {rec.confidence:>9.0f}%"
            )
            for reason in rec.reasons[:3]:
                lines.append(f"    • {reason}")
        
        if report.recovery_candidates:
            lines.extend([
                "",
                "-" * 70,
                "RECOVERY CANDIDATES (Stocks Bouncing from Lows)",
                "-" * 70,
                f"{'#':<3} {'Symbol':<12} {'Price':>10} {'From Peak':>12} {'Recovery':>12}",
                "-" * 70,
            ])
            
            for i, rec in enumerate(report.recovery_candidates[:5], 1):
                lines.append(
                    f"{i:<3} {rec.symbol:<12} {rec.current_price:>10.2f} "
                    f"{rec.decline_from_peak_pct:>11.1f}% {rec.recovery_from_low_pct:>11.1f}%"
                )
                for reason in rec.reasons[:3]:
                    lines.append(f"    • {reason}")
        
        # Add portfolio analysis section at the end
        if portfolio_insights:
            lines.append("")
            lines.append(self._portfolio_email_generator.generate_text(portfolio_insights))
        
        lines.extend([
            "",
            "=" * 70,
            "DISCLAIMER: This is for informational purposes only.",
            "Do your own research before investing.",
            "=" * 70,
        ])
        
        return "\n".join(lines)
    
    def _build_html_report(self, report: DailyReport, market_overview: Optional[MarketOverview] = None, newsletter: Optional[Newsletter] = None, portfolio_insights: Optional[PortfolioInsights] = None) -> str:
        """Build HTML report with table format."""
        
        # Build market overview section
        market_section = ""
        if market_overview:
            market_section = self._build_market_overview_html(market_overview)
        
        # Build newsletter section
        newsletter_section = ""
        newsletter_css = ""
        if newsletter:
            newsletter_section = newsletter.html_content
            newsletter_css = newsletter._newsletter_generator.get_newsletter_css() if hasattr(newsletter, '_newsletter_generator') else ""
            # Get CSS from the generator
            from app.analysis.newsletter import NewsletterGenerator
            newsletter_css = NewsletterGenerator().get_newsletter_css()
        
        # Build portfolio analysis section (appended at the end)
        portfolio_section = ""
        if portfolio_insights:
            # Extract just the body content from the portfolio HTML (remove head/html tags)
            portfolio_html = self._portfolio_email_generator.generate_html(portfolio_insights)
            # The portfolio email generator returns complete HTML, we need just the body content
            # Use a simple extraction or wrap it in a section
            portfolio_section = f'''
            <div style="margin-top: 40px; padding-top: 30px; border-top: 3px solid #1a1a2e;">
                <h2 style="color: #1a1a2e; text-align: center; margin-bottom: 20px;">
                    📊 PORTFOLIO ANALYSIS AND RECOMMENDATIONS
                </h2>
                {self._extract_portfolio_html_content(portfolio_insights)}
            </div>
            '''
        
        # Build buy signals table rows
        buy_rows = ""
        for i, rec in enumerate(report.buy_signals, 1):
            reasons_html = "<br>".join([f"• {r}" for r in rec.reasons[:3]])
            buy_rows += f"""
            <tr>
                <td>{i}</td>
                <td><strong>{rec.symbol}</strong><br><small>{rec.company_name}</small></td>
                <td>₹{rec.current_price:.2f}</td>
                <td class="target-up">₹{rec.target_price:.2f}</td>
                <td>₹{rec.stop_loss:.2f}</td>
                <td><span class="signal-buy">{rec.signal.value}</span></td>
                <td>{rec.confidence:.0f}%</td>
                <td>{rec.risk_level.value}</td>
                <td class="reasons"><small>{reasons_html}</small></td>
            </tr>
            """
        
        # Build sell signals table rows
        sell_rows = ""
        for i, rec in enumerate(report.sell_signals, 1):
            reasons_html = "<br>".join([f"• {r}" for r in rec.reasons[:3]])
            sell_rows += f"""
            <tr>
                <td>{i}</td>
                <td><strong>{rec.symbol}</strong><br><small>{rec.company_name}</small></td>
                <td>₹{rec.current_price:.2f}</td>
                <td class="target-down">₹{rec.target_price:.2f}</td>
                <td>₹{rec.stop_loss:.2f}</td>
                <td><span class="signal-sell">{rec.signal.value}</span></td>
                <td>{rec.confidence:.0f}%</td>
                <td>{rec.risk_level.value}</td>
                <td class="reasons"><small>{reasons_html}</small></td>
            </tr>
            """
        
        # Build recovery table rows
        recovery_rows = ""
        for i, rec in enumerate(report.recovery_candidates[:5], 1):
            reasons_html = "<br>".join([f"• {r}" for r in rec.reasons[:3]])
            recovery_rows += f"""
            <tr>
                <td>{i}</td>
                <td><strong>{rec.symbol}</strong><br><small>{rec.company_name}</small></td>
                <td>₹{rec.current_price:.2f}</td>
                <td>{rec.decline_from_peak_pct:.1f}%</td>
                <td>{rec.recovery_from_low_pct:.1f}%</td>
                <td>{rec.trend.value if rec.trend else 'N/A'}</td>
                <td class="reasons"><small>{reasons_html}</small></td>
            </tr>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ 
                    font-family: 'Segoe UI', Arial, sans-serif; 
                    max-width: 900px; 
                    margin: 0 auto; 
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .header {{ 
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                    color: white; 
                    padding: 25px; 
                    border-radius: 10px; 
                    margin-bottom: 25px;
                    text-align: center;
                }}
                .header h1 {{ margin: 0 0 10px 0; font-size: 24px; }}
                .header p {{ margin: 0; opacity: 0.9; }}
                .meta-container {{
                    display: flex;
                    justify-content: center;
                    gap: 15px;
                    margin-top: 15px;
                    flex-wrap: wrap;
                }}
                .meta-item {{ 
                    background: rgba(255,255,255,0.15); 
                    padding: 8px 15px; 
                    border-radius: 5px;
                    font-size: 14px;
                }}
                .section {{ 
                    background: white; 
                    border-radius: 10px; 
                    padding: 20px; 
                    margin-bottom: 20px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }}
                .section h2 {{
                    margin: 0 0 15px 0;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #eee;
                    font-size: 18px;
                }}
                .buy-section h2 {{ color: #28a745; border-color: #28a745; }}
                .sell-section h2 {{ color: #dc3545; border-color: #dc3545; }}
                .recovery-section h2 {{ color: #ffc107; border-color: #ffc107; }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 13px;
                }}
                th {{
                    background: #f8f9fa;
                    padding: 10px 8px;
                    text-align: left;
                    font-weight: 600;
                    border-bottom: 2px solid #dee2e6;
                }}
                td {{
                    padding: 10px 8px;
                    border-bottom: 1px solid #eee;
                    vertical-align: top;
                }}
                tr:hover {{ background: #f8f9fa; }}
                .signal-buy {{ 
                    background: #d4edda; 
                    color: #155724; 
                    padding: 3px 8px; 
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 11px;
                }}
                .signal-sell {{ 
                    background: #f8d7da; 
                    color: #721c24; 
                    padding: 3px 8px; 
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 11px;
                }}
                small {{ color: #666; }}
                .reasons {{ 
                    max-width: 250px;
                    line-height: 1.4;
                }}
                .target-up {{ color: #28a745; font-weight: bold; }}
                .target-down {{ color: #dc3545; font-weight: bold; }}
                .market-overview {{
                    background: white;
                    border-radius: 10px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }}
                .market-overview h2 {{
                    margin: 0 0 15px 0;
                    color: #1a1a2e;
                    font-size: 18px;
                    border-bottom: 2px solid #1a1a2e;
                    padding-bottom: 10px;
                }}
                .market-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 15px;
                    margin-bottom: 15px;
                }}
                .market-item {{
                    padding: 12px;
                    border-radius: 8px;
                    background: #f8f9fa;
                    text-align: center;
                }}
                .market-item .label {{
                    font-size: 11px;
                    color: #666;
                    text-transform: uppercase;
                    margin-bottom: 5px;
                }}
                .market-item .value {{
                    font-size: 16px;
                    font-weight: bold;
                    color: #1a1a2e;
                }}
                .market-item .change {{
                    font-size: 14px;
                    font-weight: bold;
                    margin-top: 3px;
                }}
                .up {{ color: #28a745; }}
                .down {{ color: #dc3545; }}
                .outlook-box {{
                    padding: 15px;
                    border-radius: 8px;
                    text-align: center;
                    margin-top: 15px;
                }}
                .outlook-bullish {{ background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); border: 2px solid #28a745; }}
                .outlook-bearish {{ background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%); border: 2px solid #dc3545; }}
                .outlook-neutral {{ background: linear-gradient(135deg, #fff3cd 0%, #ffeeba 100%); border: 2px solid #ffc107; }}
                .outlook-label {{ font-size: 12px; color: #666; }}
                .outlook-value {{ font-size: 20px; font-weight: bold; margin: 5px 0; }}
                .outlook-reason {{ font-size: 12px; color: #555; }}
                .disclaimer {{ 
                    font-size: 12px; 
                    color: #666; 
                    margin-top: 25px; 
                    padding: 15px; 
                    background: #fff3cd; 
                    border-radius: 8px;
                    border-left: 4px solid #ffc107;
                }}
                {newsletter_css}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Stock Market Daily Recommendation</h1>
                <p>{report.date} | {report.market_status}</p>
                <div class="meta-container">
                    <div class="meta-item">📊 {report.total_stocks_analyzed} Stocks Analyzed</div>
                    <div class="meta-item">🟢 {len(report.buy_signals)} Buy Signals</div>
                    <div class="meta-item">🔴 {len(report.sell_signals)} Sell Signals</div>
                    <div class="meta-item">🔄 {len(report.recovery_candidates)} Recovery</div>
                </div>
            </div>
            
            {market_section}
            
            {newsletter_section}
            
            <div class="section buy-section">
                <h2>🟢 TOP 10 BUY RECOMMENDATIONS</h2>
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Stock</th>
                            <th>Price</th>
                            <th>Target</th>
                            <th>Stop Loss</th>
                            <th>Signal</th>
                            <th>Conf.</th>
                            <th>Risk</th>
                            <th>Reasons</th>
                        </tr>
                    </thead>
                    <tbody>
                        {buy_rows if buy_rows else '<tr><td colspan="9" style="text-align:center;">No buy signals found</td></tr>'}
                    </tbody>
                </table>
            </div>
            
            <div class="section sell-section">
                <h2>🔴 TOP 10 SELL RECOMMENDATIONS</h2>
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Stock</th>
                            <th>Price</th>
                            <th>Target</th>
                            <th>Stop Loss</th>
                            <th>Signal</th>
                            <th>Conf.</th>
                            <th>Risk</th>
                            <th>Reasons</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sell_rows if sell_rows else '<tr><td colspan="9" style="text-align:center;">No sell signals found</td></tr>'}
                    </tbody>
                </table>
            </div>
            
            {"" if not report.recovery_candidates else f'''
            <div class="section recovery-section">
                <h2>🔄 RECOVERY CANDIDATES (Stocks Bouncing from Lows)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Stock</th>
                            <th>Price</th>
                            <th>From Peak</th>
                            <th>Recovery</th>
                            <th>Trend</th>
                            <th>Reasons</th>
                        </tr>
                    </thead>
                    <tbody>
                        {recovery_rows}
                    </tbody>
                </table>
            </div>
            '''}
            
            {portfolio_section}
            
            <div class="disclaimer">
                ⚠️ <strong>Disclaimer:</strong> This report is for informational purposes only and should not be considered as investment advice. 
                Past performance is not indicative of future results. Please do your own research and consult a financial advisor before making investment decisions.
                Generated by Stock Market Screener at {report.date}.
            </div>
        </body>
        </html>
        """
        return html
    
    def _build_market_overview_html(self, overview: MarketOverview) -> str:
        """Build HTML section for market overview."""
        
        def format_value(index, show_rupee=False):
            if not index:
                return '--', '--', ''
            color_class = "up" if index.is_up else "down"
            arrow = "▲" if index.is_up else "▼"
            if show_rupee:
                value = f"₹{index.last_close:.2f}"
            else:
                value = f"{index.last_close:,.2f}"
            change = f'<span class="{color_class}">{arrow} {abs(index.change_pct):.2f}%</span>'
            return index.name, value, change
        
        # Build table rows
        dj_name, dj_val, dj_chg = format_value(overview.dow_jones)
        nq_name, nq_val, nq_chg = format_value(overview.nasdaq)
        gn_name, gn_val, gn_chg = format_value(overview.gift_nifty)
        ui_name, ui_val, ui_chg = format_value(overview.usd_inr, show_rupee=True)
        sx_name, sx_val, sx_chg = format_value(overview.sensex)
        nf_name, nf_val, nf_chg = format_value(overview.nifty)
        
        # Determine outlook class
        outlook_class = "outlook-neutral"
        if "BULLISH" in overview.market_outlook:
            outlook_class = "outlook-bullish"
        elif "BEARISH" in overview.market_outlook:
            outlook_class = "outlook-bearish"
        
        return f'''
        <div class="market-overview">
            <h2>📈 GLOBAL MARKET OVERVIEW</h2>
            
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 15px;">
                <thead>
                    <tr style="background: #f8f9fa;">
                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6;">Market</th>
                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6;">Index</th>
                        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #dee2e6;">Last Close</th>
                        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #dee2e6;">Change</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td rowspan="2" style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold; background: #f8f9fa;">🇺🇸 US Markets</td>
                        <td style="padding: 10px; border-bottom: 1px solid #eee;">{dj_name}</td>
                        <td style="padding: 10px; text-align: right; border-bottom: 1px solid #eee;">{dj_val}</td>
                        <td style="padding: 10px; text-align: right; border-bottom: 1px solid #eee;">{dj_chg}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #eee;">{nq_name}</td>
                        <td style="padding: 10px; text-align: right; border-bottom: 1px solid #eee;">{nq_val}</td>
                        <td style="padding: 10px; text-align: right; border-bottom: 1px solid #eee;">{nq_chg}</td>
                    </tr>
                    <tr>
                        <td rowspan="2" style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold; background: #f8f9fa;">🇮🇳 Indian Markets</td>
                        <td style="padding: 10px; border-bottom: 1px solid #eee;">{sx_name}</td>
                        <td style="padding: 10px; text-align: right; border-bottom: 1px solid #eee;">{sx_val}</td>
                        <td style="padding: 10px; text-align: right; border-bottom: 1px solid #eee;">{sx_chg}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #eee;">{nf_name}</td>
                        <td style="padding: 10px; text-align: right; border-bottom: 1px solid #eee;">{nf_val}</td>
                        <td style="padding: 10px; text-align: right; border-bottom: 1px solid #eee;">{nf_chg}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold; background: #f8f9fa;">🌏 GIFT Nifty</td>
                        <td style="padding: 10px; border-bottom: 1px solid #eee;">{gn_name}</td>
                        <td style="padding: 10px; text-align: right; border-bottom: 1px solid #eee;">{gn_val}</td>
                        <td style="padding: 10px; text-align: right; border-bottom: 1px solid #eee;">{gn_chg}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold; background: #f8f9fa;">💱 Currency</td>
                        <td style="padding: 10px;">{ui_name}</td>
                        <td style="padding: 10px; text-align: right;">{ui_val}</td>
                        <td style="padding: 10px; text-align: right;">{ui_chg}</td>
                    </tr>
                </tbody>
            </table>
            
            <div class="outlook-box {outlook_class}">
                <div class="outlook-label">TODAY'S MARKET OUTLOOK</div>
                <div class="outlook-value">{overview.market_outlook}</div>
                <div class="outlook-reason">{overview.outlook_reason}</div>
            </div>
        </div>
        '''
    
    def _extract_portfolio_html_content(self, insights: PortfolioInsights) -> str:
        """Build portfolio analysis HTML content for embedding in daily report."""
        summary = insights.summary
        
        # Portfolio summary cards
        pnl_color = "#28a745" if summary.total_pnl >= 0 else "#dc3545"
        pnl_sign = "+" if summary.total_pnl >= 0 else ""
        day_color = "#28a745" if summary.day_change >= 0 else "#dc3545"
        day_sign = "+" if summary.day_change >= 0 else ""
        
        summary_html = f'''
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 25px;">
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;">
                <div style="font-size: 12px; color: #666; margin-bottom: 5px;">Total Investment</div>
                <div style="font-size: 18px; font-weight: bold;">₹{summary.total_investment:,.0f}</div>
            </div>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;">
                <div style="font-size: 12px; color: #666; margin-bottom: 5px;">Current Value</div>
                <div style="font-size: 18px; font-weight: bold;">₹{summary.current_value:,.0f}</div>
            </div>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;">
                <div style="font-size: 12px; color: #666; margin-bottom: 5px;">Total P&L</div>
                <div style="font-size: 18px; font-weight: bold; color: {pnl_color};">
                    {pnl_sign}₹{abs(summary.total_pnl):,.0f} ({pnl_sign}{summary.total_pnl_pct:.2f}%)
                </div>
            </div>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;">
                <div style="font-size: 12px; color: #666; margin-bottom: 5px;">Day Change</div>
                <div style="font-size: 18px; font-weight: bold; color: {day_color};">
                    {day_sign}{summary.day_change_pct:.2f}%
                </div>
            </div>
        </div>
        
        <div style="display: flex; justify-content: center; gap: 20px; margin-bottom: 25px;">
            <div style="text-align: center;">
                <span style="font-size: 24px; font-weight: bold;">{summary.total_stocks}</span>
                <span style="font-size: 12px; color: #666; display: block;">Total Stocks</span>
            </div>
            <div style="text-align: center;">
                <span style="font-size: 24px; font-weight: bold; color: #28a745;">{summary.profitable_stocks}</span>
                <span style="font-size: 12px; color: #666; display: block;">Profitable</span>
            </div>
            <div style="text-align: center;">
                <span style="font-size: 24px; font-weight: bold; color: #dc3545;">{summary.loss_making_stocks}</span>
                <span style="font-size: 12px; color: #666; display: block;">Loss Making</span>
            </div>
        </div>
        '''
        
        # Risk flags
        risk_flags_html = ""
        flags = summary.risk_flags.get_flags()
        if flags:
            risk_items = "".join([f'<li style="margin: 5px 0;">{flag}</li>' for flag in flags])
            risk_flags_html = f'''
            <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin-bottom: 20px; border-radius: 4px;">
                <strong>⚠️ Risk Flags</strong>
                <ul style="margin: 10px 0 0 20px; padding: 0;">{risk_items}</ul>
            </div>
            '''
        
        # Top 20 predictions table
        predictions_html = ""
        if insights.predictions:
            pred_rows = ""
            for i, h in enumerate(insights.predictions[:20], 1):
                direction_color = "#28a745" if h.predicted_direction == "UP" else "#dc3545" if h.predicted_direction == "DOWN" else "#666"
                arrow = "▲" if h.predicted_direction == "UP" else "▼" if h.predicted_direction == "DOWN" else "●"
                pnl_color = "#28a745" if h.pnl_pct >= 0 else "#dc3545"
                pnl_sign = "+" if h.pnl_pct >= 0 else ""
                pred_rows += f'''
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 8px;">{i}</td>
                    <td style="padding: 8px;"><strong>{h.symbol}</strong></td>
                    <td style="padding: 8px;">₹{h.current_price:,.2f}</td>
                    <td style="padding: 8px; color: {pnl_color};">{pnl_sign}{h.pnl_pct:.1f}%</td>
                    <td style="padding: 8px; color: {direction_color}; font-weight: bold;">{arrow} {h.predicted_direction}</td>
                    <td style="padding: 8px;">{h.predicted_confidence:.0f}%</td>
                    <td style="padding: 8px; font-size: 12px;">{h.prediction_reason}</td>
                </tr>
                '''
            predictions_html = f'''
            <div style="margin-bottom: 25px;">
                <h3 style="color: #1a1a2e; margin-bottom: 15px;">📈 Top 20 Stock Movement Predictions</h3>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <thead>
                        <tr style="background: #f8f9fa;">
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6;">#</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6;">Symbol</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6;">Price</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6;">P&L</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6;">Direction</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6;">Confidence</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6;">Reason</th>
                        </tr>
                    </thead>
                    <tbody>{pred_rows}</tbody>
                </table>
            </div>
            '''
        
        # Portfolio news
        news_html = ""
        if insights.portfolio_news:
            news_items = ""
            for item in insights.portfolio_news[:10]:
                sentiment_color = "#28a745" if item.sentiment == "positive" else "#dc3545" if item.sentiment == "negative" else "#666"
                sentiment_icon = "+" if item.sentiment == "positive" else "-" if item.sentiment == "negative" else "•"
                news_items += f'''
                <div style="padding: 10px; border-bottom: 1px solid #eee;">
                    <span style="color: {sentiment_color}; font-weight: bold;">[{sentiment_icon}]</span>
                    {item.headline}
                    <span style="font-size: 11px; color: #999; display: block; margin-top: 3px;">Source: {item.source}</span>
                </div>
                '''
            news_html = f'''
            <div style="margin-bottom: 25px;">
                <h3 style="color: #1a1a2e; margin-bottom: 15px;">📰 Relevant News for Your Portfolio</h3>
                <div style="background: #f8f9fa; border-radius: 8px; overflow: hidden;">
                    {news_items}
                </div>
            </div>
            '''
        
        # Buy/Hold/Sell signals
        signals_html = self._build_portfolio_signals_html(insights)
        
        return summary_html + risk_flags_html + predictions_html + news_html + signals_html
    
    def _build_portfolio_signals_html(self, insights: PortfolioInsights) -> str:
        """Build Buy/Hold/Sell signals HTML section."""
        sections = []
        
        # Aggressive Buy section
        if insights.aggressive_buy_stocks:
            rows = ""
            for h in insights.aggressive_buy_stocks[:5]:
                reasons_html = "<br>".join([f"• {r}" for r in h.reasons[:2]])
                rows += f'''
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 10px;"><strong>{h.symbol}</strong></td>
                    <td style="padding: 10px;">₹{h.current_price:,.2f}</td>
                    <td style="padding: 10px; color: {"#28a745" if h.pnl_pct >= 0 else "#dc3545"};">{h.pnl_pct:+.1f}%</td>
                    <td style="padding: 10px;">{h.fundamental_score:.0f}/100</td>
                    <td style="padding: 10px; font-size: 11px;">{reasons_html}</td>
                </tr>
                '''
            sections.append(f'''
            <div style="margin-bottom: 20px;">
                <h4 style="color: #28a745; margin-bottom: 10px;">🟢 AGGRESSIVE BUY (Average on Dips)</h4>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <thead><tr style="background: #d4edda;">
                        <th style="padding: 8px; text-align: left;">Symbol</th>
                        <th style="padding: 8px; text-align: left;">Price</th>
                        <th style="padding: 8px; text-align: left;">P&L</th>
                        <th style="padding: 8px; text-align: left;">Score</th>
                        <th style="padding: 8px; text-align: left;">Reasons</th>
                    </tr></thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
            ''')
        
        # Buy on Dip section
        if insights.buy_on_dip_stocks:
            symbols = ", ".join([h.symbol for h in insights.buy_on_dip_stocks[:10]])
            sections.append(f'''
            <div style="margin-bottom: 20px;">
                <h4 style="color: #17a2b8; margin-bottom: 10px;">🔵 BUY ON DIP</h4>
                <p style="background: #d1ecf1; padding: 12px; border-radius: 4px;">{symbols}</p>
            </div>
            ''')
        
        # Hold section
        if insights.hold_stocks:
            symbols = ", ".join([h.symbol for h in insights.hold_stocks[:15]])
            sections.append(f'''
            <div style="margin-bottom: 20px;">
                <h4 style="color: #6c757d; margin-bottom: 10px;">⚪ HOLD</h4>
                <p style="background: #e9ecef; padding: 12px; border-radius: 4px;">{symbols}</p>
            </div>
            ''')
        
        # Reduce section
        if insights.reduce_stocks:
            symbols = ", ".join([h.symbol for h in insights.reduce_stocks[:10]])
            sections.append(f'''
            <div style="margin-bottom: 20px;">
                <h4 style="color: #ffc107; margin-bottom: 10px;">🟡 REDUCE (Book Partial Profits)</h4>
                <p style="background: #fff3cd; padding: 12px; border-radius: 4px;">{symbols}</p>
            </div>
            ''')
        
        # Exit section
        if insights.exit_stocks:
            rows = ""
            for h in insights.exit_stocks:
                reasons_html = "<br>".join([f"⚠️ {r}" for r in h.reasons[:2]])
                rows += f'''
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 10px;"><strong>{h.symbol}</strong></td>
                    <td style="padding: 10px;">₹{h.current_price:,.2f}</td>
                    <td style="padding: 10px; color: #dc3545;">{h.pnl_pct:+.1f}%</td>
                    <td style="padding: 10px;">{h.fundamental_score:.0f}/100</td>
                    <td style="padding: 10px; font-size: 11px;">{reasons_html}</td>
                </tr>
                '''
            sections.append(f'''
            <div style="margin-bottom: 20px;">
                <h4 style="color: #dc3545; margin-bottom: 10px;">🔴 EXIT (Weak Fundamentals)</h4>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <thead><tr style="background: #f8d7da;">
                        <th style="padding: 8px; text-align: left;">Symbol</th>
                        <th style="padding: 8px; text-align: left;">Price</th>
                        <th style="padding: 8px; text-align: left;">P&L</th>
                        <th style="padding: 8px; text-align: left;">Score</th>
                        <th style="padding: 8px; text-align: left;">Reasons</th>
                    </tr></thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
            ''')
        
        # Strategy notes
        strategy_html = f'''
        <div style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); padding: 20px; border-radius: 8px; margin-top: 20px;">
            <h4 style="color: #1565c0; margin: 0 0 10px 0;">📋 Strategy Notes</h4>
            <p style="margin: 0; color: #1a1a2e;">{insights.market_outlook}</p>
            <p style="margin: 10px 0 0 0; font-size: 13px; color: #555;">{insights.strategy_notes}</p>
        </div>
        '''
        
        return f'''
        <div style="margin-top: 25px;">
            <h3 style="color: #1a1a2e; margin-bottom: 15px; border-bottom: 2px solid #1a1a2e; padding-bottom: 10px;">
                📊 BUY / HOLD / SELL SIGNALS
            </h3>
            {"".join(sections)}
            {strategy_html}
        </div>
        '''
