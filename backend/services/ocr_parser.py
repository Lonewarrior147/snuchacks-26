"""Tesseract OCR → structured transaction parser (SBI format).

SBI bank statement format example:
    20/03/2026  UPI-RELIANCE GAS       3,000.00 Dr   7,000.00
    21/03/2026  NEFT-SHARMA WEDDING    7,000.00 Cr  14,000.00
"""

import re
from datetime import datetime

import pytesseract
from PIL import Image

from config import TESSERACT_CMD

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# Regex for SBI bank statement lines
SBI_PATTERN = re.compile(
    r"(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s+(Cr|Dr)\s+([\d,]+\.\d{2})"
)


def extract_text_from_image(image_path: str) -> str:
    """Run Tesseract OCR on an image file and return raw text."""
    image = Image.open(image_path)
    raw_text = pytesseract.image_to_string(image)
    return raw_text


def parse_sbi_transactions(raw_text: str) -> list[dict]:
    """
    Parse SBI-format bank statement text into structured transactions.

    Returns list of dicts with keys:
        counterparty_name, transaction_type, amount, balance_after, created_at
    """
    transactions = []
    lines = raw_text.split("\n")

    for line in lines:
        match = SBI_PATTERN.search(line)
        if match:
            date_str = match.group(1)
            counterparty = match.group(2).strip()
            amount_str = match.group(3).replace(",", "")
            cr_dr = match.group(4)
            balance_str = match.group(5).replace(",", "")

            try:
                txn_date = datetime.strptime(date_str, "%d/%m/%Y")
                amount = float(amount_str)
                balance_after = float(balance_str)
            except (ValueError, TypeError):
                continue

            transactions.append(
                {
                    "counterparty_name": counterparty,
                    "transaction_type": "credit" if cr_dr == "Cr" else "debit",
                    "amount": amount,
                    "balance_after": balance_after,
                    "created_at": txn_date,
                }
            )

    return transactions


def process_bank_statement(image_path: str) -> list[dict]:
    """Full pipeline: image → OCR text → parsed transactions."""
    raw_text = extract_text_from_image(image_path)
    return parse_sbi_transactions(raw_text)
