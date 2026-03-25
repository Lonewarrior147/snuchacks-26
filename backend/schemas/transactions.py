from datetime import datetime

from pydantic import BaseModel


class TransactionOut(BaseModel):
    id: int
    user_id: int
    counterparty_name: str
    transaction_type: str
    amount: float
    balance_after: float
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionsResponse(BaseModel):
    transactions: list[TransactionOut]
