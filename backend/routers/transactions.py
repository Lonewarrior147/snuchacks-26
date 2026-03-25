"""Transactions router: GET /transactions"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User, Transaction
from schemas.transactions import TransactionOut, TransactionsResponse
from utils.auth_utils import get_current_user

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=TransactionsResponse)
async def list_transactions(
    limit: int = Query(default=50, ge=1, le=200),
    type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all transactions for the user."""
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)

    if type:
        query = query.filter(Transaction.transaction_type == type)

    transactions = (
        query.order_by(Transaction.created_at.desc())
        .limit(limit)
        .all()
    )

    return TransactionsResponse(
        transactions=[TransactionOut.model_validate(t) for t in transactions]
    )
