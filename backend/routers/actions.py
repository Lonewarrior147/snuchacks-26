"""Actions router: GET /actions, POST /actions/{id}/action-taken, POST /actions/{id}/delay"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.connection import get_db
from database.models import User, Payable, Receivable, DailyExpense, Transaction, InsightCache
from schemas.actions import ActionsResponse, ActionItem, ActionFactors, DelayRequest
from services.decision_engine import generate_recommendations
from utils.auth_utils import get_current_user

router = APIRouter(prefix="/actions", tags=["actions"])


@router.get("", response_model=ActionsResponse)
async def get_actions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """All pending/delayed payables, scored and ranked by obligation score."""
    total_cash = current_user.bank_balance + current_user.petty_cash

    daily_burn = (
        db.query(func.coalesce(func.sum(DailyExpense.amount), 0.0))
        .filter(DailyExpense.user_id == current_user.id, DailyExpense.is_active == True)
        .scalar()
    )

    payables = (
        db.query(Payable)
        .filter(Payable.user_id == current_user.id)
        .all()
    )

    receivables = (
        db.query(Receivable)
        .filter(Receivable.user_id == current_user.id, Receivable.status == "pending")
        .all()
    )

    daily_expenses = (
        db.query(DailyExpense)
        .filter(DailyExpense.user_id == current_user.id, DailyExpense.is_active == True)
        .all()
    )

    actions = generate_recommendations(
        payables=payables,
        receivables=receivables,
        daily_expenses=daily_expenses,
        current_cash=total_cash,
        daily_burn=daily_burn,
    )

    total_pending = sum(
        p.amount for p in payables if p.status in ("pending", "delayed")
    )

    action_items = [
        ActionItem(
            id=a["id"],
            name=a["name"],
            amount=a["amount"],
            due_date=a["due_date"],
            category=a["category"],
            status=a["status"],
            obligation_score=a["obligation_score"],
            priority_label=a["priority_label"],
            recommendation=a["recommendation"],
            reasoning=a["reasoning"],
            factors=ActionFactors(**a["factors"]),
        )
        for a in actions
    ]

    return ActionsResponse(
        actions=action_items,
        total_pending=total_pending,
        available_cash=total_cash,
    )


@router.post("/{payable_id}/action-taken")
async def action_taken(
    payable_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    User confirms action taken on payable (paid it externally).
    Updates balance and logs transaction. Returns updated dashboard summary.
    """
    payable = (
        db.query(Payable)
        .filter(Payable.id == payable_id, Payable.user_id == current_user.id)
        .first()
    )

    if not payable:
        raise HTTPException(status_code=404, detail="Payable not found")

    if payable.status == "paid":
        raise HTTPException(status_code=400, detail="Payable already paid")

    if current_user.bank_balance < payable.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    # 1. Mark as paid
    payable.status = "paid"

    # 2. Deduct from bank balance
    current_user.bank_balance -= payable.amount

    # 3. Log transaction
    transaction = Transaction(
        user_id=current_user.id,
        counterparty_name=payable.name,
        transaction_type="debit",
        amount=payable.amount,
        balance_after=current_user.bank_balance,
    )
    db.add(transaction)

    # 4. Invalidate insights cache
    db.query(InsightCache).filter(InsightCache.user_id == current_user.id).delete()

    db.commit()
    db.refresh(current_user)

    # Return updated dashboard summary
    from routers.dashboard import _compute_dashboard
    return _compute_dashboard(current_user, db)


@router.post("/{payable_id}/delay")
async def delay_payable(
    payable_id: int,
    request: DelayRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delay a payable. Pushes due_date forward by delay_days."""
    payable = (
        db.query(Payable)
        .filter(Payable.id == payable_id, Payable.user_id == current_user.id)
        .first()
    )

    if not payable:
        raise HTTPException(status_code=404, detail="Payable not found")

    # 1. Update status and due date
    payable.status = "delayed"
    payable.due_date = payable.due_date + timedelta(days=request.delay_days)

    # 2. Invalidate insights cache
    db.query(InsightCache).filter(InsightCache.user_id == current_user.id).delete()

    db.commit()
    db.refresh(payable)

    # Recalculate obligation score for this item
    from services.obligation_scorer import score_payable
    score_info = score_payable(payable)

    return {
        "id": payable.id,
        "name": payable.name,
        "amount": payable.amount,
        "due_date": payable.due_date,
        "status": payable.status,
        "obligation_score": score_info["obligation_score"],
        "priority_label": score_info["priority_label"],
    }
