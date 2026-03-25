"""Days-to-Zero calculation engine.

Day-by-day forward cash simulation over 30 days.
"""

from datetime import date, timedelta
from typing import Optional


def calculate_days_to_zero(
    current_cash: float,
    payables: list,
    receivables: list,
    daily_burn: float,
) -> tuple[int, list[dict], Optional[date]]:
    """
    Simulate cash balance day-by-day for 30 days.

    Args:
        current_cash: bank_balance + petty_cash
        payables: list of Payable ORM objects (status != 'paid')
        receivables: list of Receivable ORM objects (status == 'pending')
        daily_burn: sum of active daily expenses

    Returns:
        (days_to_zero, projections_list, zero_date_or_none)
    """
    today = date.today()
    running_balance = current_cash
    projections = []
    zero_date = None

    for day_offset in range(31):
        current_date = today + timedelta(days=day_offset)

        # Daily burn rate
        outflows = daily_burn

        # Payables due on this date (pending or delayed)
        for p in payables:
            if p.due_date == current_date and p.status != "paid":
                outflows += p.amount

        # Receivables expected on this date (confidence-weighted)
        inflows = 0.0
        for r in receivables:
            if r.expected_date == current_date and r.status == "pending":
                inflows += r.amount * r.confidence

        running_balance = running_balance - outflows + inflows

        projections.append(
            {
                "date": current_date,
                "projected_balance": round(running_balance, 2),
                "inflows": round(inflows, 2),
                "outflows": round(outflows, 2),
            }
        )

        if running_balance <= 0 and zero_date is None:
            zero_date = current_date
            return day_offset, projections, zero_date

    return 30, projections, zero_date
