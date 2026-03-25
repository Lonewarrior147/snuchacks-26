"""Deterministic action recommendation engine.

Scores all payables, simulates payment feasibility, generates recommendations
with reasoning strings.
"""

from datetime import date

from services.obligation_scorer import score_payable
from services.days_to_zero import calculate_days_to_zero


def generate_recommendations(
    payables: list,
    receivables: list,
    daily_expenses: list,
    current_cash: float,
    daily_burn: float,
) -> list[dict]:
    """
    Full decision engine pipeline:
    1. Score and sort
    2. Simulate payment feasibility
    3. Generate recommendations
    4. Add non-payment actions
    5. Attach deterministic reasoning

    Returns list of action item dicts.
    """
    today = date.today()

    # Step 1: Score and sort
    active_payables = [p for p in payables if p.status != "paid"]
    scored = []
    for p in active_payables:
        score_info = score_payable(p)
        scored.append((p, score_info))

    scored.sort(key=lambda x: x[1]["obligation_score"], reverse=True)

    # Pre-compute baseline DTZ
    baseline_dtz, _, _ = calculate_days_to_zero(
        current_cash, active_payables, receivables, daily_burn
    )

    # Step 2 & 3: Simulate feasibility and generate recommendations
    actions = []
    simulated_cash = current_cash

    for payable, score_info in scored:
        days_until_due = (payable.due_date - today).days
        cash_availability = min(100, int((simulated_cash / max(payable.amount, 1)) * 100))

        # Add cash_availability to factors
        score_info["factors"]["cash_availability"] = cash_availability

        # Determine recommendation
        if simulated_cash >= payable.amount:
            # Simulate: if we pay this, what happens to DTZ?
            remaining_payables = [
                p for p, _ in scored if p.id != payable.id and p.status != "paid"
            ]
            sim_cash = simulated_cash - payable.amount
            sim_dtz, _, _ = calculate_days_to_zero(
                sim_cash, remaining_payables, receivables, daily_burn
            )

            if sim_dtz < 2:
                recommendation = "delay"
                reasoning = (
                    f"Cash insufficient. Acting now drops runway to {sim_dtz} days. "
                    f"Delay by 7 days recommended."
                )
            else:
                recommendation = "action_needed"
                reasoning = _build_action_reasoning(payable, days_until_due)
                simulated_cash -= payable.amount
        elif score_info["obligation_score"] >= 50 and simulated_cash >= payable.amount * 0.5:
            recommendation = "negotiate_partial"
            reasoning = (
                f"High priority but insufficient cash for full payment. "
                f"Consider 50% payment of ₹{payable.amount / 2:,.0f} to maintain relationship."
            )
        elif payable.flexibility >= 70 and payable.operational_importance < 20:
            recommendation = "cancel"
            reasoning = (
                f"Low priority. ₹{payable.amount:,.0f}/month can be redirected to critical expenses."
            )
        else:
            recommendation = "delay"
            reasoning = (
                f"Insufficient cash (₹{simulated_cash:,.0f} available vs ₹{payable.amount:,.0f} needed). "
                f"Delay until cash position improves."
            )

        actions.append({
            "id": payable.id,
            "name": payable.name,
            "amount": payable.amount,
            "due_date": payable.due_date,
            "category": payable.category,
            "status": payable.status,
            "obligation_score": score_info["obligation_score"],
            "priority_label": score_info["priority_label"],
            "recommendation": recommendation,
            "reasoning": reasoning,
            "factors": score_info["factors"],
        })

    # Step 4: Non-payment actions (appended as special items)
    for r in receivables:
        if r.status == "overdue":
            actions.append(_receivable_action(
                r, "Follow up",
                f"Follow up on ₹{r.amount:,.0f} from {r.source} — payment is overdue.",
            ))
        elif r.confidence < 0.5 and r.status == "pending":
            actions.append(_receivable_action(
                r, "Chase payment",
                f"Chase payment from {r.source} — reliability declining (confidence: {r.confidence:.0%}).",
            ))

    return actions


def _build_action_reasoning(payable, days_until_due: int) -> str:
    """Build templated reasoning for action_needed recommendation."""
    parts = []
    if days_until_due <= 0:
        parts.append("Overdue.")
    else:
        parts.append(f"Due in {days_until_due} days.")

    if payable.penalty_risk >= 70:
        parts.append("High penalty risk.")
    if payable.operational_importance >= 80:
        parts.append("Critical for daily operations.")
    if payable.category == "vendor":
        parts.append("Supply cutoff risk.")
    elif payable.category == "salary":
        parts.append("Staff retention at stake.")

    return " ".join(parts)


def _receivable_action(receivable, title: str, reasoning: str) -> dict:
    """Create a pseudo action item for receivable follow-ups."""
    return {
        "id": receivable.id * -1,  # Negative ID to distinguish from payables
        "name": f"{title}: {receivable.source}",
        "amount": receivable.amount,
        "due_date": receivable.expected_date,
        "category": "receivable",
        "status": receivable.status,
        "obligation_score": 0,
        "priority_label": "High" if receivable.status == "overdue" else "Medium",
        "recommendation": "follow_up",
        "reasoning": reasoning,
        "factors": {
            "urgency": 100 if receivable.status == "overdue" else 70,
            "penalty_risk": 0,
            "operational_importance": 80,
            "cash_availability": 0,
            "flexibility": 0,
        },
    }
