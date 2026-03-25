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


# def process_bank_statement(image_path: str) -> list[dict]:
#     """Full pipeline: image → OCR text → parsed transactions."""
#     raw_text = extract_text_from_image(image_path)
#     return parse_sbi_transactions(raw_text)

def process_bank_statement(image_path: str) -> list[dict]:
    """
    Full pipeline:
    image → OCR → regex parsing → fallback Gemini
    """
    raw_text = extract_text_from_image(image_path)

    # Step 1: Try SBI regex parser
    transactions = parse_sbi_transactions(raw_text)

    # Step 2: Fallback to Gemini if regex fails
    if not transactions:
        print("⚠️ Regex failed, using Gemini fallback...")
        transactions = parse_with_gemini(raw_text)

    return transactions

import json
import google.generativeai as genai

genai.configure(api_key="AIzaSyCbQnl49PmsMrKaZrNxWAPPb608wNsMY_s")
gemini_model = genai.GenerativeModel('gemini-2.5-flash')

def parse_with_gemini(raw_text: str) -> list[dict]:
    """
    Fallback parser using Gemini when regex fails.
    """

    prompt = f"""
You are a financial data parser.

Extract transaction data from the OCR text.

Return ONLY valid JSON (no explanation).

Format:
[
  {{
    "counterparty_name": "string",
    "transaction_type": "credit/debit",
    "amount": float,
    "balance_after": float,
    "created_at": "YYYY-MM-DD"
  }}
]

OCR TEXT:
{raw_text}
"""

    response = gemini_model.generate_content(prompt)
    raw = response.text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]

    try:
        data = json.loads(raw)

        # Convert date string → datetime
        for txn in data:
            txn["created_at"] = datetime.strptime(txn["created_at"], "%Y-%m-%d")

        return data

    except Exception as e:
        print("Gemini parsing failed:", e)
        print("Raw response:", raw)
        return []



