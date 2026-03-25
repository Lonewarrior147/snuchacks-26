from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NewsItemOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    category: str
    severity: str
    source_url: Optional[str] = None
    published_at: Optional[datetime] = None
    time_ago: str = ""

    model_config = {"from_attributes": True}


class NewsResponse(BaseModel):
    news: list[NewsItemOut]


class NewsRefreshResponse(BaseModel):
    new_items: int
    total_items: int
