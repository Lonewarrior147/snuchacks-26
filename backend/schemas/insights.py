from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SmartSummary(BaseModel):
    deficit: float
    days_to_zero: int
    daily_burn_rate: float
    total_recommendations: int
    urgent_count: int
    moderate_count: int


class InsightCard(BaseModel):
    id: int
    type: str  # action / warning / opportunity / critical
    priority: str  # urgent / moderate / low
    title: str
    description: str
    potential_savings: Optional[float] = None
    generated_at: datetime

    model_config = {"from_attributes": True}


class InsightsResponse(BaseModel):
    smart_summary: SmartSummary
    insights: list[InsightCard]
