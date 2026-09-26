"""Fetch current and upcoming IPO details from InvestorGain."""

import logging
import re
from datetime import date, datetime, timedelta
from html import escape
from typing import Any, Optional
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

IPO_GMP_URL = "https://www.investorgain.com/report/ipo-gmp-live/331/"
IPO_DISCLAIMER = (
    "Grey market premium is unofficial, unregulated and indicative only. "
    "It does not guarantee listing gains or represent investment advice."
)


class IPOTracker:
    """Collect IPO dates, price details, and indicative grey-market data."""

    def fetch(self) -> dict[str, Any]:
        fetched_at = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
        result: dict[str, Any] = {
            "source": "InvestorGain",
            "source_url": IPO_GMP_URL,
            "fetched_at": fetched_at,
            "disclaimer": IPO_DISCLAIMER,
            "open": [],
            "upcoming": [],
        }

        try:
            response = requests.get(
                IPO_GMP_URL,
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.find("table", id="reportTable")
            if table is None:
                raise ValueError("IPO GMP table was not found")

            india_today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
            for row in table.select("tbody tr"):
                ipo = self._parse_row(row, india_today)
                if ipo is not None:
                    result["open" if ipo["status"] == "open" else "upcoming"].append(ipo)

            for key in ("open", "upcoming"):
                result[key].sort(
                    key=lambda ipo: (
                        ipo["gmp_pct"] is not None,
                        ipo["gmp_pct"] if ipo["gmp_pct"] is not None else -float("inf"),
                    ),
                    reverse=True,
                )
        except Exception as error:
            logger.warning("Failed to fetch IPO data from InvestorGain: %s", error)
            result["error"] = str(error)

        return result

    @classmethod
    def _parse_row(cls, row: Any, today: date) -> Optional[dict[str, Any]]:
        cells = {
            cell.get("data-label", "").strip(): cell
            for cell in row.select("td[data-label]")
        }
        name_cell = cells.get("Name")
        gmp_cell = cells.get("GMP")
        if not name_cell or not gmp_cell:
            return None

        status_badge = next(
            (badge for badge in name_cell.select("span") if badge.get_text(" ", strip=True) in {"O", "U"}),
            None,
        )
        status_code = status_badge.get_text(" ", strip=True) if status_badge else ""
        if status_code not in {"O", "U"}:
            return None

        name_link = name_cell.select_one("a")
        name = name_link.get_text(" ", strip=True) if name_link else name_cell.get_text(" ", strip=True)
        venue_badge = name_cell.select_one("span.bg-secondary")
        exchange = venue_badge.get_text(" ", strip=True) if venue_badge else ""
        source_url = urljoin(IPO_GMP_URL, name_link.get("href", "")) if name_link else IPO_GMP_URL

        gmp_text = gmp_cell.get_text(" ", strip=True)
        gmp_match = re.search(
            r"₹\s*(--|[-+]?\d[\d,]*(?:\.\d+)?)\s*\(\s*([-+]?\d[\d,]*(?:\.\d+)?)%",
            gmp_text,
        )
        gmp = cls._number(gmp_match.group(1)) if gmp_match and gmp_match.group(1) != "--" else None
        gmp_pct = cls._number(gmp_match.group(2)) if gmp_match and gmp is not None else None

        issue_price_cell = cells.get("Price (₹)")
        issue_price = cls._number(issue_price_cell.get_text(" ", strip=True) if issue_price_cell else "")
        issue_size = cells.get("IPO Size")
        lot_cell = cells.get("Lot")
        lot_size = cls._number(lot_cell.get_text(" ", strip=True) if lot_cell else "")
        subscription = cells.get("Sub")
        rating = cells.get("Rating")
        anchor = cells.get("Anchor")

        return {
            "name": name,
            "exchange": exchange,
            "category": "SME" if "SME" in exchange.upper() else "Mainboard",
            "status": "open" if status_code == "O" else "upcoming",
            "gmp": gmp,
            "gmp_pct": gmp_pct,
            "issue_price": issue_price,
            "estimated_listing_price": issue_price + gmp if issue_price is not None and gmp is not None else None,
            "market_read": cls._market_read(gmp_pct, subscription.get_text(" ", strip=True) if subscription else ""),
            "issue_size": issue_size.get_text(" ", strip=True) if issue_size else "",
            "lot_size": int(lot_size) if lot_size is not None else None,
            "open_date": cls._date(cells.get("Open"), today),
            "close_date": cls._date(cells.get("Close"), today),
            "allotment_date": cls._date(cells.get("BoA Dt"), today),
            "listing_date": cls._date(cells.get("Listing"), today),
            "subscription": subscription.get_text(" ", strip=True) if subscription else "",
            "rating": rating.get_text(" ", strip=True) if rating else "",
            "anchor_status": anchor.get_text(" ", strip=True) if anchor else "",
            "source_updated": cells.get("Updated-On").get_text(" ", strip=True) if cells.get("Updated-On") else "",
            "source_url": source_url,
        }

    @staticmethod
    def _number(value: str) -> Optional[float]:
        match = re.search(r"[-+]?\d[\d,]*(?:\.\d+)?", value.replace("₹", ""))
        return float(match.group(0).replace(",", "")) if match else None

    @staticmethod
    def _market_read(gmp_pct: Optional[float], subscription: str) -> str:
        if gmp_pct is None:
            read = "No GMP quote reported; a GMP-based listing estimate is unavailable."
        elif gmp_pct < 0:
            read = "Negative unofficial premium indicates weak grey-market sentiment in this snapshot."
        elif gmp_pct == 0:
            read = "No premium is indicated in the current grey-market snapshot."
        elif gmp_pct >= 20:
            read = "Strong positive GMP snapshot, but grey-market quotes are unofficial and can reverse."
        else:
            read = "Positive but modest GMP snapshot; it is not a reliable listing forecast."

        subscribed = re.search(r"\d+(?:\.\d+)?", subscription)
        if subscribed:
            read += f" Overall subscription reported at {subscribed.group(0)}x."
        return read

    @staticmethod
    def email_html(data: dict[str, Any]) -> str:
        """Render compact open/upcoming IPO analysis for an email client."""
        sections = []
        for key, title in (("open", "TOP 5 OPEN IPOs"), ("upcoming", "TOP 5 UPCOMING IPOs")):
            cards = []
            for ipo in data.get(key, [])[:5]:
                gmp = f"₹{ipo['gmp']:,.2f} ({ipo['gmp_pct']:+.2f}%)" if ipo.get("gmp_pct") is not None else "Not reported"
                estimate = f"₹{ipo['estimated_listing_price']:,.2f}" if ipo.get("estimated_listing_price") is not None else "Unavailable"
                issue_price = f"₹{ipo['issue_price']:,.2f}" if ipo.get("issue_price") is not None else "Not reported"
                dates = " · ".join(
                    f"{label}: {datetime.fromisoformat(ipo[field]).strftime('%d %b %Y')}"
                    for label, field in (("Open", "open_date"), ("Close", "close_date"), ("Allotment", "allotment_date"), ("Listing", "listing_date"))
                    if ipo.get(field)
                ) or "Dates not available"
                cards.append(f"""
                    <tr><td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;">
                        <strong style="color:#0f172a;">{escape(ipo.get('name', 'IPO'))}</strong>
                        <span style="color:#64748b;font-size:10px;"> · {escape(ipo.get('category', 'IPO'))} · {escape(ipo.get('exchange', ''))}</span><br>
                        <span style="font-size:11px;color:#334155;">Issue {issue_price} · GMP {gmp} · Est. listing {estimate}</span><br>
                        <span style="font-size:10px;color:#64748b;">{escape(dates)} · Size {escape(ipo.get('issue_size') or 'N/A')} · Lot {escape(str(ipo.get('lot_size') or 'N/A'))} · Subscription {escape(ipo.get('subscription') or 'N/A')}</span><br>
                        <span style="font-size:10px;color:#475569;">{escape(ipo.get('market_read', ''))}</span>
                        <a href="{escape(ipo.get('source_url', IPO_GMP_URL), quote=True)}" style="font-size:10px;color:#047857;"> Source details</a>
                    </td></tr>""")
            body = "".join(cards) or '<tr><td style="padding:10px;color:#64748b;">No IPO data available.</td></tr>'
            sections.append(f"""
                <tr><td style="padding:0 16px 12px;">
                    <table role="presentation" width="100%" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;">
                        <tr><td style="padding:11px 12px 5px;color:#0f172a;font-size:11px;font-weight:700;">{title}</td></tr>
                        {body}
                    </table>
                </td></tr>""")

        fetched_at = data.get("fetched_at")
        updated = datetime.fromisoformat(fetched_at).strftime("%d %b %Y, %I:%M %p IST") if fetched_at else "Update time unavailable"
        return f"""
            <tr><td style="padding:0 16px 8px;">
                <span style="font-size:11px;font-weight:700;color:#64748b;">IPO CALENDAR & GREY-MARKET SNAPSHOT</span>
                <span style="font-size:9px;color:#94a3b8;"> · Updated {escape(updated)}</span>
            </td></tr>
            {''.join(sections)}
            <tr><td style="padding:0 16px 16px;color:#64748b;font-size:9px;line-height:1.5;">
                {escape(data.get('disclaimer', IPO_DISCLAIMER))} Ranking reflects reported GMP%, not IPO quality or an investment recommendation.
            </td></tr>"""

    @staticmethod
    def email_text(data: dict[str, Any]) -> str:
        """Render a plain-text IPO snapshot for the email alternative body."""
        lines = ["IPO CALENDAR & GREY-MARKET SNAPSHOT", "=" * 42]
        for key, title in (("open", "TOP 5 OPEN IPOs"), ("upcoming", "TOP 5 UPCOMING IPOs")):
            lines.extend(("", title, "-" * len(title)))
            ipos = data.get(key, [])[:5]
            if not ipos:
                lines.append("No IPO data available.")
            for ipo in ipos:
                gmp = f"₹{ipo['gmp']:,.2f} ({ipo['gmp_pct']:+.2f}%)" if ipo.get("gmp_pct") is not None else "Not reported"
                estimate = f"₹{ipo['estimated_listing_price']:,.2f}" if ipo.get("estimated_listing_price") is not None else "Unavailable"
                lines.extend((
                    f"{ipo.get('name', 'IPO')} ({ipo.get('category', 'IPO')} / {ipo.get('exchange', 'venue unavailable')})",
                    f"Issue: ₹{ipo['issue_price']:,.2f}" if ipo.get("issue_price") is not None else "Issue: Not reported",
                    f"GMP: {gmp} | Est. listing: {estimate}",
                    f"Open: {ipo.get('open_date') or 'N/A'} | Close: {ipo.get('close_date') or 'N/A'} | Allotment: {ipo.get('allotment_date') or 'N/A'} | Listing: {ipo.get('listing_date') or 'N/A'}",
                    f"Issue size: {ipo.get('issue_size') or 'N/A'} | Lot: {ipo.get('lot_size') or 'N/A'} | Subscription: {ipo.get('subscription') or 'N/A'}",
                    ipo.get("market_read", ""),
                    f"Source: {ipo.get('source_url', IPO_GMP_URL)}",
                    "",
                ))
        lines.append(data.get("disclaimer", IPO_DISCLAIMER))
        lines.append("Ranking reflects reported GMP%, not IPO quality or an investment recommendation.")
        return "\n".join(lines)

    @staticmethod
    def _date(cell: Any, today: date) -> Optional[str]:
        if not cell:
            return None
        match = re.search(r"\b(\d{1,2}-[A-Za-z]{3})\b", cell.get_text(" ", strip=True))
        if not match:
            return None
        parsed = datetime.strptime(match.group(1), "%d-%b").date().replace(year=today.year)
        if parsed < today and (today - parsed) > timedelta(days=180):
            parsed = parsed.replace(year=today.year + 1)
        elif parsed > today and (parsed - today) > timedelta(days=180):
            parsed = parsed.replace(year=today.year - 1)
        return parsed.isoformat()