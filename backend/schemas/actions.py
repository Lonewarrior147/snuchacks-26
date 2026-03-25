from datetime import date
from typing import Optional

from pydantic import BaseModel


class ActionFactors(BaseModel):
    urgency: int
    penalty_risk: int
    operational_importance: int
    cash_availability: int
    flexibility: int


class ActionItem(BaseModel):
    id: int
    name: str
    amount: float
    due_date: date
    category: str
    status: str
    obligation_score: float
    priority_label: str
    recommendation: str
    reasoning: str
    factors: ActionFactors


class ActionsResponse(BaseModel):
    actions: list[ActionItem]
    total_pending: float
    available_cash: float


class DelayRequest(BaseModel):
    delay_days: int = 7
