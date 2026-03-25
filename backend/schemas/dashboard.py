from typing import Optional
from datetime import date

from pydantic import BaseModel


class AlertInfo(BaseModel):
    type: str  # critical / warning
    message: str


class RecentNewsItem(BaseModel):
    id: int
    title: str
    category: str


class PendingReceivableNotification(BaseModel):
    id: int
    source: str
    amount: float
    expected_date: date
    status: str
    is_due_today: bool


class DashboardSummary(BaseModel):
    business_name: str
    bank_balance: float
    petty_cash: float
    total_cash: float
    total_receivables: float
    total_payables: float
    net_cash_flow: float
    daily_burn_rate: float
    days_to_zero: int
    upcoming_expenses_7d: float
    expected_income_7d: float
    alert: Optional[AlertInfo] = None
    recent_news: list[RecentNewsItem] = []
    pending_receivable_notifications: list[PendingReceivableNotification] = []


class CashFlowPoint(BaseModel):
    date: date
    projected_balance: float
    inflows: float
    outflows: float


class CashFlowResponse(BaseModel):
    projections: list[CashFlowPoint]
    zero_date: Optional[date] = None
