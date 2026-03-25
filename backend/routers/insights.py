"""Insights router: GET /insights, POST /insights/refresh, DELETE /insights/cache"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.connection import get_db
from database.models import (
    User, Payable, Receivable, DailyExpense, NewsItem, InsightCache,
)
from schemas.insights import InsightsResponse, SmartSummary, InsightCard
from services.days_to_zero import calculate_days_to_zero
from services.obligation_scorer import score_payable
from services.llm_service import llm_service
from utils.auth_utils import get_current_user

router = APIRouter(prefix="/insights", tags=["insights"])

CACHE_TTL_HOURS = 1


def _gather_financial_context(user: User, db: Session) -> dict:
    """Gather all financial context needed for insight generation."""
    total_cash = user.bank_balance + user.petty_cash

    daily_burn = (
        db.query(func.coalesce(func.sum(DailyExpense.amount), 0.0))
        .filter(DailyExpense.user_id == user.id, DailyExpense.is_active == True)
        .scalar()
    )

    pending_payables = (
        db.query(Payable)
        .filter(Payable.user_id == user.id, Payable.status.in_(["pending", "delayed"]))
        .all()
    )
    total_payables = sum(p.amount for p in pending_payables)

    pending_receivables = (
        db.query(Receivable)
        .filter(Receivable.user_id == user.id, Receivable.status == "pending")
        .all()
    )
    total_receivables = sum(r.amount for r in pending_receivables)

    overdue_receivables = (
        db.query(Receivable)
        .filter(Receivable.user_id == user.id, Receivable.status == "overdue")
        .all()
    )
    overdue_amount = sum(r.amount for r in overdue_receivables)

    dtz, _, _ = calculate_days_to_zero(
        total_cash, pending_payables, pending_receivables, daily_burn
    )

    # Top 5 obligations
    scored = []
    for p in pending_payables:
        info = score_payable(p)
        scored.append({
            "name": p.name,
            "amount": p.amount,
            "due_date": str(p.due_date),
            "category": p.category,
            "obligation_score": info["obligation_score"],
            "priority_label": info["priority_label"],
            "flexibility": p.flexibility,
            "operational_importance": p.operational_importance,
        })
    scored.sort(key=lambda x: x["obligation_score"], reverse=True)
    top_obligations = scored[:5]

    # Recent news
    recent_news = (
        db.query(NewsItem)
        .order_by(NewsItem.published_at.desc())
        .limit(5)
        .all()
    )
    news_list = [
        {"title": n.title, "category": n.category, "severity": n.severity}
        for n in recent_news
    ]

    return {
        "total_cash": total_cash,
        "days_to_zero": dtz,
        "daily_burn": daily_burn,
        "total_payables": total_payables,
        "payables_count": len(pending_payables),
        "total_receivables": total_receivables,
        "receivables_count": len(pending_receivables),
        "overdue_count": len(overdue_receivables),
        "overdue_amount": overdue_amount,
        "top_obligations": top_obligations,
        "recent_news": news_list,
    }


def _build_smart_summary(ctx: dict, insights_count: int, insights: list) -> SmartSummary:
    """Compute smart summary from live data."""
    urgent_count = sum(1 for i in insights if i.get("priority") == "urgent")
    moderate_count = sum(1 for i in insights if i.get("priority") == "moderate")

    deficit = ctx["total_cash"] - ctx["total_payables"]

    return SmartSummary(
        deficit=deficit,
        days_to_zero=ctx["days_to_zero"],
        daily_burn_rate=ctx["daily_burn"],
        total_recommendations=insights_count,
        urgent_count=urgent_count,
        moderate_count=moderate_count,
    )


def _generate_and_cache(user: User, db: Session, ctx: dict) -> list[InsightCache]:
    """Generate insights via LLM and store in cache."""
    # Delete existing cache
    db.query(InsightCache).filter(InsightCache.user_id == user.id).delete()

    # Generate via LLM
    raw_insights = llm_service.generate_insights(ctx)

    cached = []
    for insight in raw_insights:
        cache_entry = InsightCache(
            user_id=user.id,
            insight_type=insight.get("type", "action"),
            title=insight.get("title", ""),
            description=insight.get("description", ""),
            priority=insight.get("priority", "moderate"),
            potential_savings=insight.get("potential_savings"),
        )
        db.add(cache_entry)
        cached.append(cache_entry)

    db.commit()
    for c in cached:
        db.refresh(c)
    return cached


@router.get("", response_model=InsightsResponse)
async def get_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns LLM-generated insights. Serves from cache if fresh (< 1 hour old)."""
    ctx = _gather_financial_context(current_user, db)

    # Check cache freshness
    cutoff = datetime.utcnow() - timedelta(hours=CACHE_TTL_HOURS)
    cached = (
        db.query(InsightCache)
        .filter(
            InsightCache.user_id == current_user.id,
            InsightCache.generated_at > cutoff,
        )
        .all()
    )

    if cached:
        insight_dicts = [
            {"priority": c.priority, "type": c.insight_type} for c in cached
        ]
        smart_summary = _build_smart_summary(ctx, len(cached), insight_dicts)
        return InsightsResponse(
            smart_summary=smart_summary,
            insights=[
                InsightCard(
                    id=c.id,
                    type=c.insight_type,
                    priority=c.priority,
                    title=c.title,
                    description=c.description or "",
                    potential_savings=c.potential_savings,
                    generated_at=c.generated_at,
                )
                for c in cached
            ],
        )

    # Stale or empty — regenerate
    cached = _generate_and_cache(current_user, db, ctx)
    insight_dicts = [
        {"priority": c.priority, "type": c.insight_type} for c in cached
    ]
    smart_summary = _build_smart_summary(ctx, len(cached), insight_dicts)

    return InsightsResponse(
        smart_summary=smart_summary,
        insights=[
            InsightCard(
                id=c.id,
                type=c.insight_type,
                priority=c.priority,
                title=c.title,
                description=c.description or "",
                potential_savings=c.potential_savings,
                generated_at=c.generated_at,
            )
            for c in cached
        ],
    )


@router.post("/refresh", response_model=InsightsResponse)
async def refresh_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Force regenerate insights via LLM, even if cache is fresh."""
    ctx = _gather_financial_context(current_user, db)
    cached = _generate_and_cache(current_user, db, ctx)

    insight_dicts = [
        {"priority": c.priority, "type": c.insight_type} for c in cached
    ]
    smart_summary = _build_smart_summary(ctx, len(cached), insight_dicts)

    return InsightsResponse(
        smart_summary=smart_summary,
        insights=[
            InsightCard(
                id=c.id,
                type=c.insight_type,
                priority=c.priority,
                title=c.title,
                description=c.description or "",
                potential_savings=c.potential_savings,
                generated_at=c.generated_at,
            )
            for c in cached
        ],
    )


@router.delete("/cache")
async def clear_cache(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually clear insights cache for this user."""
    deleted = (
        db.query(InsightCache)
        .filter(InsightCache.user_id == current_user.id)
        .delete()
    )
    db.commit()
    return {"deleted_count": deleted}
