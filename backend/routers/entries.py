"""Entries router: Full CRUD for payables, receivables, daily expenses.

Includes mark-received and reschedule for receivables.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.connection import get_db
from database.models import (
    User, Payable, Receivable, DailyExpense, Transaction, InsightCache,
)
from schemas.entries import (
    PayableCreate, PayableUpdate, PayableOut,
    ReceivableCreate, ReceivableUpdate, ReceivableOut, RescheduleRequest,
    DailyExpenseCreate, DailyExpenseUpdate, DailyExpenseOut,
)
from services.obligation_scorer import apply_category_defaults
from utils.auth_utils import get_current_user

router = APIRouter(prefix="/entries", tags=["entries"])


def _invalidate_insights(db: Session, user_id: int):
    """Delete all insights_cache rows for a user."""
    db.query(InsightCache).filter(InsightCache.user_id == user_id).delete()


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  PAYABLES CRUD                                                      ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.get("/payables")
async def list_payables(
    status: Optional[str] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Payable).filter(Payable.user_id == current_user.id)
    if status:
        query = query.filter(Payable.status == status)
    if category:
        query = query.filter(Payable.category == category)
    payables = query.all()
    return {"payables": [PayableOut.model_validate(p) for p in payables]}


@router.get("/payables/{id}")
async def get_payable(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payable = db.query(Payable).filter(
        Payable.id == id, Payable.user_id == current_user.id
    ).first()
    if not payable:
        raise HTTPException(status_code=404, detail="Payable not found")
    return PayableOut.model_validate(payable)


@router.post("/payables", status_code=201)
async def create_payable(
    request: PayableCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Apply category defaults if scores not provided
    defaults = apply_category_defaults(request.category)

    payable = Payable(
        user_id=current_user.id,
        name=request.name,
        amount=request.amount,
        due_date=request.due_date,
        category=request.category,
        penalty_risk=request.penalty_risk if request.penalty_risk is not None else defaults["penalty_risk"],
        operational_importance=request.operational_importance if request.operational_importance is not None else defaults["operational_importance"],
        flexibility=request.flexibility if request.flexibility is not None else defaults["flexibility"],
        is_recurring=request.is_recurring,
        recurrence_interval=request.recurrence_interval,
    )
    db.add(payable)
    _invalidate_insights(db, current_user.id)
    db.commit()
    db.refresh(payable)
    return PayableOut.model_validate(payable)


@router.put("/payables/{id}")
async def update_payable(
    id: int,
    request: PayableUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payable = db.query(Payable).filter(
        Payable.id == id, Payable.user_id == current_user.id
    ).first()
    if not payable:
        raise HTTPException(status_code=404, detail="Payable not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(payable, field, value)

    _invalidate_insights(db, current_user.id)
    db.commit()
    db.refresh(payable)
    return PayableOut.model_validate(payable)


@router.delete("/payables/{id}")
async def delete_payable(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payable = db.query(Payable).filter(
        Payable.id == id, Payable.user_id == current_user.id
    ).first()
    if not payable:
        raise HTTPException(status_code=404, detail="Payable not found")

    db.delete(payable)
    _invalidate_insights(db, current_user.id)
    db.commit()
    return {"detail": "Payable deleted"}


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  RECEIVABLES CRUD + mark-received + reschedule                      ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.get("/receivables")
async def list_receivables(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Receivable).filter(Receivable.user_id == current_user.id)
    if status:
        query = query.filter(Receivable.status == status)
    receivables = query.all()
    return {"receivables": [ReceivableOut.model_validate(r) for r in receivables]}


@router.get("/receivables/{id}")
async def get_receivable(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    receivable = db.query(Receivable).filter(
        Receivable.id == id, Receivable.user_id == current_user.id
    ).first()
    if not receivable:
        raise HTTPException(status_code=404, detail="Receivable not found")
    return ReceivableOut.model_validate(receivable)


@router.post("/receivables", status_code=201)
async def create_receivable(
    request: ReceivableCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    receivable = Receivable(
        user_id=current_user.id,
        source=request.source,
        amount=request.amount,
        expected_date=request.expected_date,
        confidence=request.confidence,
    )
    db.add(receivable)
    _invalidate_insights(db, current_user.id)
    db.commit()
    db.refresh(receivable)
    return ReceivableOut.model_validate(receivable)


@router.put("/receivables/{id}")
async def update_receivable(
    id: int,
    request: ReceivableUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    receivable = db.query(Receivable).filter(
        Receivable.id == id, Receivable.user_id == current_user.id
    ).first()
    if not receivable:
        raise HTTPException(status_code=404, detail="Receivable not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(receivable, field, value)

    _invalidate_insights(db, current_user.id)
    db.commit()
    db.refresh(receivable)
    return ReceivableOut.model_validate(receivable)


@router.delete("/receivables/{id}")
async def delete_receivable(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    receivable = db.query(Receivable).filter(
        Receivable.id == id, Receivable.user_id == current_user.id
    ).first()
    if not receivable:
        raise HTTPException(status_code=404, detail="Receivable not found")

    db.delete(receivable)
    _invalidate_insights(db, current_user.id)
    db.commit()
    return {"detail": "Receivable deleted"}


@router.post("/receivables/{id}/mark-received")
async def mark_received(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    User confirms money has been received.
    Updates bank balance and logs a credit transaction.
    Returns updated dashboard summary.
    """
    receivable = db.query(Receivable).filter(
        Receivable.id == id, Receivable.user_id == current_user.id
    ).first()

    if not receivable:
        raise HTTPException(status_code=404, detail="Receivable not found")

    if receivable.status == "received":
        raise HTTPException(status_code=400, detail="Receivable already marked as received")

    # 1. Mark as received
    receivable.status = "received"

    # 2. Add to bank balance
    current_user.bank_balance += receivable.amount

    # 3. Log credit transaction
    transaction = Transaction(
        user_id=current_user.id,
        counterparty_name=receivable.source,
        transaction_type="credit",
        amount=receivable.amount,
        balance_after=current_user.bank_balance,
    )
    db.add(transaction)

    # 4. Invalidate insights cache
    _invalidate_insights(db, current_user.id)

    db.commit()
    db.refresh(current_user)

    # Return updated dashboard summary
    from routers.dashboard import _compute_dashboard
    return _compute_dashboard(current_user, db)


@router.post("/receivables/{id}/reschedule")
async def reschedule_receivable(
    id: int,
    request: RescheduleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    User says money was NOT received on expected date.
    Pushes expected_date forward and reduces confidence.
    """
    receivable = db.query(Receivable).filter(
        Receivable.id == id, Receivable.user_id == current_user.id
    ).first()

    if not receivable:
        raise HTTPException(status_code=404, detail="Receivable not found")

    # 1. Update expected date
    receivable.expected_date = request.new_expected_date

    # 2. Reduce confidence
    if request.reduce_confidence:
        receivable.confidence = max(0.1, receivable.confidence - 0.15)

    # 3. If confidence drops below 0.3, mark as overdue
    if receivable.confidence < 0.3:
        receivable.status = "overdue"

    # 4. Invalidate insights cache
    _invalidate_insights(db, current_user.id)

    db.commit()
    db.refresh(receivable)
    return ReceivableOut.model_validate(receivable)


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  DAILY EXPENSES CRUD                                                ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.get("/daily-expenses")
async def list_daily_expenses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    expenses = (
        db.query(DailyExpense)
        .filter(DailyExpense.user_id == current_user.id)
        .all()
    )
    daily_burn_rate = sum(e.amount for e in expenses if e.is_active)
    return {
        "daily_expenses": [DailyExpenseOut.model_validate(e) for e in expenses],
        "daily_burn_rate": daily_burn_rate,
    }


@router.post("/daily-expenses", status_code=201)
async def create_daily_expense(
    request: DailyExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    expense = DailyExpense(
        user_id=current_user.id,
        description=request.description,
        amount=request.amount,
    )
    db.add(expense)
    _invalidate_insights(db, current_user.id)
    db.commit()
    db.refresh(expense)
    return DailyExpenseOut.model_validate(expense)


@router.put("/daily-expenses/{id}")
async def update_daily_expense(
    id: int,
    request: DailyExpenseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    expense = db.query(DailyExpense).filter(
        DailyExpense.id == id, DailyExpense.user_id == current_user.id
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Daily expense not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(expense, field, value)

    _invalidate_insights(db, current_user.id)
    db.commit()
    db.refresh(expense)
    return DailyExpenseOut.model_validate(expense)


@router.delete("/daily-expenses/{id}")
async def delete_daily_expense(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    expense = db.query(DailyExpense).filter(
        DailyExpense.id == id, DailyExpense.user_id == current_user.id
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Daily expense not found")

    db.delete(expense)
    _invalidate_insights(db, current_user.id)
    db.commit()
    return {"detail": "Daily expense deleted"}
