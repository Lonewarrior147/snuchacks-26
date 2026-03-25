"""Obligation scoring model.

Weighted formula: urgency + penalty_risk + operational_importance + flexibility
"""

from datetime import date

# Category defaults applied when user doesn't specify scores
CATEGORY_DEFAULTS = {
    "vendor": {"penalty_risk": 70, "operational_importance": 90, "flexibility": 15},
    "salary": {"penalty_risk": 80, "operational_importance": 85, "flexibility": 5},
    "rent": {"penalty_risk": 90, "operational_importance": 70, "flexibility": 5},
    "emi": {"penalty_risk": 95, "operational_importance": 50, "flexibility": 0},
    "utility": {"penalty_risk": 30, "operational_importance": 30, "flexibility": 60},
    "subscription": {"penalty_risk": 10, "operational_importance": 15, "flexibility": 90},
}


def compute_urgency(due_date: date) -> int:
    """Compute urgency score from due_date relative to today."""
    days_until_due = (due_date - date.today()).days

    if days_until_due <= 0:
        return 100  # overdue
    elif days_until_due <= 2:
        return 90
    elif days_until_due <= 3:
        return 85
    elif days_until_due <= 5:
        return 70
    elif days_until_due <= 7:
        return 60
    elif days_until_due <= 14:
        return 40
    else:
        return 30


def score_payable(payable) -> dict:
    """
    Score a single payable and return obligation_score, priority_label, urgency,
    and the full factors breakdown.

    Args:
        payable: Payable ORM object

    Returns:
        dict with keys: obligation_score, priority_label, urgency, factors
    """
    urgency = compute_urgency(payable.due_date)

    # Use stored values; they are either user-provided or category defaults
    penalty_risk = payable.penalty_risk
    operational_importance = payable.operational_importance
    flexibility = payable.flexibility

    obligation_score = (
        (0.30 * urgency)
        + (0.25 * penalty_risk)
        + (0.30 * operational_importance)
        + (0.15 * (100 - flexibility))
    )
    obligation_score = round(obligation_score, 1)

    # Priority label
    if obligation_score >= 80:
        priority_label = "High"
    elif obligation_score >= 50:
        priority_label = "Medium"
    else:
        priority_label = "Low"

    return {
        "obligation_score": obligation_score,
        "priority_label": priority_label,
        "urgency": urgency,
        "factors": {
            "urgency": urgency,
            "penalty_risk": penalty_risk,
            "operational_importance": operational_importance,
            "flexibility": flexibility,
        },
    }


def apply_category_defaults(category: str) -> dict:
    """Return default scoring values for a category."""
    return CATEGORY_DEFAULTS.get(
        category,
        {"penalty_risk": 50, "operational_importance": 50, "flexibility": 50},
    )
