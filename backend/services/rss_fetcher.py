"""RSS feed fetcher for food industry news.

Fetches from configured RSS URLs, parses entries, strips HTML,
assigns categories from URL mapping, and deduplicates by source_url.
"""

from datetime import datetime, timezone
from typing import Optional

import feedparser
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from config import RSS_FEED_URLS, RSS_CATEGORY_MAP
from database.models import NewsItem


def _get_category_for_url(url: str) -> str:
    """Determine news category from the feed URL domain."""
    for domain_fragment, category in RSS_CATEGORY_MAP.items():
        if domain_fragment in url:
            return category
    return "market_trend"


def _strip_html(raw_html: Optional[str]) -> Optional[str]:
    """Remove HTML tags from a string using BeautifulSoup."""
    if not raw_html:
        return None
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def _parse_published_date(entry) -> Optional[datetime]:
    """Extract published date from a feedparser entry."""
    published_parsed = entry.get("published_parsed")
    if published_parsed:
        try:
            return datetime(*published_parsed[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass
    return None


def fetch_and_store_news(db: Session) -> dict:
    """
    Fetch all configured RSS feeds, parse entries, store new items.

    Returns:
        dict with keys: new_items (int), total_items (int)
    """
    new_count = 0

    for feed_url in RSS_FEED_URLS:
        feed_url = feed_url.strip()
        if not feed_url:
            continue

        category = _get_category_for_url(feed_url)

        try:
            feed = feedparser.parse(feed_url)
        except Exception:
            continue

        for entry in feed.entries:
            source_url = entry.get("link")
            if not source_url:
                continue

            # Dedup check
            existing = (
                db.query(NewsItem)
                .filter(NewsItem.source_url == source_url)
                .first()
            )
            if existing:
                continue

            title = entry.get("title", "Untitled")
            description = _strip_html(entry.get("summary") or entry.get("description"))
            published_at = _parse_published_date(entry)

            news_item = NewsItem(
                title=title,
                description=description,
                category=category,
                severity="info",
                source_url=source_url,
                published_at=published_at,
                fetched_at=datetime.now(timezone.utc),
            )

            try:
                db.add(news_item)
                db.flush()
                new_count += 1
            except IntegrityError:
                db.rollback()
                continue

    db.commit()

    total_items = db.query(NewsItem).count()

    return {"new_items": new_count, "total_items": total_items}
