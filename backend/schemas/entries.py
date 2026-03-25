from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


# ── Payable ───────────────────────────────────────────────────────────

class PayableCreate(BaseModel):
    name: str
    amount: float
    due_date: date
    category: str  # vendor/salary/rent/utility/subscription/emi
    penalty_risk: Optional[int] = None
    operational_importance: Optional[int] = None
    flexibility: Optional[int] = None
    is_recurring: bool = False
    recurrence_interval: Optional[str] = None


class PayableUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    due_date: Optional[date] = None
    category: Optional[str] = None
    penalty_risk: Optional[int] = None
    operational_importance: Optional[int] = None
    flexibility: Optional[int] = None
    is_recurring: Optional[bool] = None
    recurrence_interval: Optional[str] = None
    status: Optional[str] = None


class PayableOut(BaseModel):
    id: int
    user_id: int
    name: str
    amount: float
    due_date: date
    category: str
    penalty_risk: int
    operational_importance: int
    flexibility: int
    is_recurring: bool
    recurrence_interval: Optional[str] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Receivable ────────────────────────────────────────────────────────

class ReceivableCreate(BaseModel):
    source: str
    amount: float
    expected_date: date
    confidence: float = 0.8


class ReceivableUpdate(BaseModel):
    source: Optional[str] = None
    amount: Optional[float] = None
    expected_date: Optional[date] = None
    confidence: Optional[float] = None
    status: Optional[str] = None


class ReceivableOut(BaseModel):
    id: int
    user_id: int
    source: str
    amount: float
    expected_date: date
    confidence: float
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RescheduleRequest(BaseModel):
    new_expected_date: date
    reduce_confidence: bool = True


# ── Daily Expense ─────────────────────────────────────────────────────

class DailyExpenseCreate(BaseModel):
    description: str
    amount: float


class DailyExpenseUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[float] = None
    is_active: Optional[bool] = None


class DailyExpenseOut(BaseModel):
    id: int
    user_id: int
    description: str
    amount: float
    is_active: bool

    model_config = {"from_attributes": True}
