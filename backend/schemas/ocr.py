from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TransactionParsed(BaseModel):
    id: int
    user_id: int
    counterparty_name: str
    transaction_type: str
    amount: float
    balance_after: float
    created_at: datetime

    model_config = {"from_attributes": True}


class OCRUploadResponse(BaseModel):
    transactions_parsed: int
    transactions: list[TransactionParsed]
    updated_balance: float
