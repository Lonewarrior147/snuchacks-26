"""News router: GET /news, POST /news/refresh"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User, NewsItem
from schemas.news import NewsItemOut, NewsResponse, NewsRefreshResponse
from services.rss_fetcher import fetch_and_store_news
from utils.auth_utils import get_current_user
from utils.helpers import time_ago

router = APIRouter(prefix="/news", tags=["news"])


@router.get("", response_model=NewsResponse)
async def get_news(
    limit: int = Query(default=20, ge=1, le=100),
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns food industry news, fetched from RSS feeds."""
    query = db.query(NewsItem)

    if category:
        query = query.filter(NewsItem.category == category)

    news_items = (
        query.order_by(NewsItem.published_at.desc())
        .limit(limit)
        .all()
    )

    result = []
    for item in news_items:
        out = NewsItemOut.model_validate(item)
        out.time_ago = time_ago(item.published_at) if item.published_at else ""
        result.append(out)

    return NewsResponse(news=result)


@router.post("/refresh", response_model=NewsRefreshResponse)
async def refresh_news(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger RSS feed fetch. Parses feeds, stores new articles."""
    result = fetch_and_store_news(db)
    return NewsRefreshResponse(
        new_items=result["new_items"],
        total_items=result["total_items"],
    )
