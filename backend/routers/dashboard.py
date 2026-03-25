"""Dashboard router: GET /dashboard/summary, GET /dashboard/cashflow"""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.connection import get_db
from database.models import User, Payable, Receivable, DailyExpense, NewsItem
from schemas.dashboard import (
    DashboardSummary,
    AlertInfo,
    RecentNewsItem,
    PendingReceivableNotification,
    CashFlowResponse,
    CashFlowPoint,
)
from services.days_to_zero import calculate_days_to_zero
from utils.auth_utils import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _compute_dashboard(user: User, db: Session) -> DashboardSummary:
    """Compute all dashboard metrics for a user."""
    today = date.today()

    # Core values
    bank_balance = user.bank_balance
    petty_cash = user.petty_cash
    total_cash = bank_balance + petty_cash

    # Daily burn rate
    daily_burn = (
        db.query(func.coalesce(func.sum(DailyExpense.amount), 0.0))
        .filter(DailyExpense.user_id == user.id, DailyExpense.is_active == True)
        .scalar()
    )

    # Payables
    pending_payables = (
        db.query(Payable)
        .filter(Payable.user_id == user.id, Payable.status.in_(["pending", "delayed"]))
        .all()
    )
    total_payables = sum(p.amount for p in pending_payables)

    # Receivables
    pending_receivables = (
        db.query(Receivable)
        .filter(Receivable.user_id == user.id, Receivable.status == "pending")
        .all()
    )
    total_receivables = sum(r.amount for r in pending_receivables)

    # Net cash flow
    net_cash_flow = total_cash + total_receivables - total_payables

    # Days to zero
    dtz, _, _ = calculate_days_to_zero(
        total_cash, pending_payables, pending_receivables, daily_burn
    )

    # Upcoming expenses (7 days)
    seven_days = today + timedelta(days=7)
    upcoming_payables_7d = sum(
        p.amount for p in pending_payables if p.due_date <= seven_days
    )
    upcoming_expenses_7d = upcoming_payables_7d + (daily_burn * 7)

    # Expected income (7 days)
    expected_income_7d = sum(
        r.amount for r in pending_receivables if r.expected_date <= seven_days
    )

    # Alert
    alert: Optional[AlertInfo] = None
    if dtz <= 3:
        alert = AlertInfo(type="critical", message=f"Cash shortfall expected in {dtz} days")
    elif dtz <= 7:
        alert = AlertInfo(type="warning", message=f"Cash may run low in {dtz} days")

    # Recent news (3 items)
    recent_news_items = (
        db.query(NewsItem)
        .order_by(NewsItem.published_at.desc())
        .limit(3)
        .all()
    )
    recent_news = [
        RecentNewsItem(id=n.id, title=n.title, category=n.category)
        for n in recent_news_items
    ]

    # Pending receivable notifications (expected_date <= today, status = pending)
    due_receivables = [
        r for r in pending_receivables if r.expected_date <= today
    ]
    pending_receivable_notifications = [
        PendingReceivableNotification(
            id=r.id,
            source=r.source,
            amount=r.amount,
            expected_date=r.expected_date,
            status=r.status,
            is_due_today=(r.expected_date == today),
        )
        for r in due_receivables
    ]

    return DashboardSummary(
        business_name=user.business_name,
        bank_balance=bank_balance,
        petty_cash=petty_cash,
        total_cash=total_cash,
        total_receivables=total_receivables,
        total_payables=total_payables,
        net_cash_flow=net_cash_flow,
        daily_burn_rate=daily_burn,
        days_to_zero=dtz,
        upcoming_expenses_7d=upcoming_expenses_7d,
        expected_income_7d=expected_income_7d,
        alert=alert,
        recent_news=recent_news,
        pending_receivable_notifications=pending_receivable_notifications,
    )


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Single call to load the entire dashboard. Computes all metrics server-side."""
    return _compute_dashboard(current_user, db)


@router.get("/cashflow", response_model=CashFlowResponse)
async def get_cashflow(
    days: int = Query(default=7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Daily projected cash balances for the chart."""
    total_cash = current_user.bank_balance + current_user.petty_cash

    daily_burn = (
        db.query(func.coalesce(func.sum(DailyExpense.amount), 0.0))
        .filter(DailyExpense.user_id == current_user.id, DailyExpense.is_active == True)
        .scalar()
    )

    payables = (
        db.query(Payable)
        .filter(Payable.user_id == current_user.id, Payable.status.in_(["pending", "delayed"]))
        .all()
    )

    receivables = (
        db.query(Receivable)
        .filter(Receivable.user_id == current_user.id, Receivable.status == "pending")
        .all()
    )

    _, projections, zero_date = calculate_days_to_zero(
        total_cash, payables, receivables, daily_burn
    )

    # Limit to requested number of days
    projections = projections[:days]

    return CashFlowResponse(
        projections=[CashFlowPoint(**p) for p in projections],
        zero_date=zero_date,
    )
