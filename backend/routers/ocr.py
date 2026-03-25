"""OCR router: POST /ocr/upload"""

import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User, Transaction, InsightCache
from schemas.ocr import OCRUploadResponse, TransactionParsed
from services.ocr_parser import process_bank_statement
from utils.auth_utils import get_current_user

router = APIRouter(prefix="/ocr", tags=["ocr"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")


@router.post("/upload", response_model=OCRUploadResponse)
async def upload_bank_statement(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a bank statement image (SBI format).
    Tesseract extracts text. Parser creates structured transactions.
    """
    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: jpg, png, pdf",
        )

    # Save uploaded file
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "png"
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Process via OCR
    try:
        parsed_transactions = process_bank_statement(file_path)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"OCR processing failed: {str(e)}")

    if not parsed_transactions:
        raise HTTPException(status_code=422, detail="No transactions could be parsed from the image")

    # Store transactions and update balance
    stored = []
    for txn_data in parsed_transactions:
        transaction = Transaction(
            user_id=current_user.id,
            counterparty_name=txn_data["counterparty_name"],
            transaction_type=txn_data["transaction_type"],
            amount=txn_data["amount"],
            balance_after=txn_data["balance_after"],
            created_at=txn_data["created_at"],
        )
        db.add(transaction)
        db.flush()
        stored.append(transaction)

    # Update user's bank balance to the last transaction's balance_after
    last_balance = parsed_transactions[-1]["balance_after"]
    current_user.bank_balance = last_balance

    # Invalidate insights cache
    db.query(InsightCache).filter(InsightCache.user_id == current_user.id).delete()

    db.commit()
    for t in stored:
        db.refresh(t)

    return OCRUploadResponse(
        transactions_parsed=len(stored),
        transactions=[TransactionParsed.model_validate(t) for t in stored],
        updated_balance=last_balance,
    )
