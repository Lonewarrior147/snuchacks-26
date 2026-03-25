"""Seed script to populate the database with demo data for CashDabba."""

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from database.connection import SessionLocal, engine, Base
from database.models import (
    User,
    Transaction,
    Payable,
    Receivable,
    DailyExpense,
    NewsItem,
)
from utils.auth_utils import hash_password


def seed_database():
    """Create tables and insert demo data."""
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    # Check if already seeded
    if db.query(User).first():
        print("Database already seeded. Skipping.")
        db.close()
        return

    today = date.today()

    # ── User ──────────────────────────────────────────────────────────
    user = User(
        name="Lakshmi Devi",
        email="lakshmi@annapurna.in",
        phone="9876543210",
        password_hash=hash_password("cashdabba123"),
        language="en",
        business_name="Annapurna Tiffins",
        business_type="tiffin",
        bank_balance=10000.0,
        petty_cash=500.0,
    )
    db.add(user)
    db.flush()

    # ── Payables ──────────────────────────────────────────────────────
    payables = [
        Payable(
            user_id=user.id,
            name="Vegetable Supplier - Koyambedu",
            amount=4000.0,
            due_date=today + timedelta(days=2),
            category="vendor",
            penalty_risk=70,
            operational_importance=95,
            flexibility=10,
            is_recurring=True,
            recurrence_interval="weekly",
            status="pending",
        ),
        Payable(
            user_id=user.id,
            name="Rice & Daal Wholesale",
            amount=3500.0,
            due_date=today + timedelta(days=4),
            category="vendor",
            penalty_risk=60,
            operational_importance=90,
            flexibility=20,
            is_recurring=True,
            recurrence_interval="monthly",
            status="pending",
        ),
        Payable(
            user_id=user.id,
            name="Staff Salary - Cook Ramu",
            amount=5000.0,
            due_date=today + timedelta(days=5),
            category="salary",
            penalty_risk=80,
            operational_importance=85,
            flexibility=5,
            is_recurring=True,
            recurrence_interval="monthly",
            status="pending",
        ),
        Payable(
            user_id=user.id,
            name="Shop Rent",
            amount=8000.0,
            due_date=today + timedelta(days=7),
            category="rent",
            penalty_risk=90,
            operational_importance=70,
            flexibility=5,
            is_recurring=True,
            recurrence_interval="monthly",
            status="pending",
        ),
        Payable(
            user_id=user.id,
            name="Electricity Bill",
            amount=1800.0,
            due_date=today + timedelta(days=10),
            category="utility",
            penalty_risk=30,
            operational_importance=30,
            flexibility=60,
            is_recurring=True,
            recurrence_interval="monthly",
            status="pending",
        ),
        Payable(
            user_id=user.id,
            name="Zomato Subscription",
            amount=1000.0,
            due_date=today + timedelta(days=12),
            category="subscription",
            penalty_risk=10,
            operational_importance=15,
            flexibility=90,
            is_recurring=True,
            recurrence_interval="monthly",
            status="pending",
        ),
        Payable(
            user_id=user.id,
            name="Gas Cylinder Refill",
            amount=2000.0,
            due_date=today + timedelta(days=3),
            category="vendor",
            penalty_risk=50,
            operational_importance=85,
            flexibility=15,
            is_recurring=False,
            status="pending",
        ),
    ]
    db.add_all(payables)

    # ── Receivables ───────────────────────────────────────────────────
    receivables = [
        Receivable(
            user_id=user.id,
            source="Wedding Catering - Sharma",
            amount=7000.0,
            expected_date=today,
            confidence=0.8,
            status="pending",
        ),
        Receivable(
            user_id=user.id,
            source="Corporate Lunch Order - TCS",
            amount=3000.0,
            expected_date=today + timedelta(days=3),
            confidence=0.9,
            status="pending",
        ),
        Receivable(
            user_id=user.id,
            source="Temple Festival Catering",
            amount=5000.0,
            expected_date=today + timedelta(days=6),
            confidence=0.6,
            status="pending",
        ),
        Receivable(
            user_id=user.id,
            source="Monthly Tiffin - Apartment Complex",
            amount=4500.0,
            expected_date=today + timedelta(days=1),
            confidence=0.95,
            status="pending",
        ),
    ]
    db.add_all(receivables)

    # ── Daily Expenses ────────────────────────────────────────────────
    daily_expenses = [
        DailyExpense(
            user_id=user.id,
            description="Daily vegetable purchase",
            amount=800.0,
            is_active=True,
        ),
        DailyExpense(
            user_id=user.id,
            description="Cooking oil & spices",
            amount=300.0,
            is_active=True,
        ),
        DailyExpense(
            user_id=user.id,
            description="Packaging & delivery",
            amount=400.0,
            is_active=True,
        ),
        DailyExpense(
            user_id=user.id,
            description="Fuel / transport",
            amount=250.0,
            is_active=True,
        ),
        DailyExpense(
            user_id=user.id,
            description="Miscellaneous / chai / snacks",
            amount=250.0,
            is_active=True,
        ),
    ]
    db.add_all(daily_expenses)

    # ── Transactions (recent history) ─────────────────────────────────
    transactions = [
        Transaction(
            user_id=user.id,
            counterparty_name="Koyambedu Vegetables",
            transaction_type="debit",
            amount=3500.0,
            balance_after=13500.0,
            created_at=datetime.now() - timedelta(days=5),
        ),
        Transaction(
            user_id=user.id,
            counterparty_name="Daily Tiffin Collections",
            transaction_type="credit",
            amount=2500.0,
            balance_after=16000.0,
            created_at=datetime.now() - timedelta(days=4),
        ),
        Transaction(
            user_id=user.id,
            counterparty_name="Gas Supplier",
            transaction_type="debit",
            amount=2000.0,
            balance_after=14000.0,
            created_at=datetime.now() - timedelta(days=3),
        ),
        Transaction(
            user_id=user.id,
            counterparty_name="Birthday Party Catering",
            transaction_type="credit",
            amount=4000.0,
            balance_after=18000.0,
            created_at=datetime.now() - timedelta(days=2),
        ),
        Transaction(
            user_id=user.id,
            counterparty_name="Staff Advance - Ramu",
            transaction_type="debit",
            amount=1000.0,
            balance_after=17000.0,
            created_at=datetime.now() - timedelta(days=1),
        ),
    ]
    db.add_all(transactions)

    # ── News Items (placeholder – real ones come from RSS) ────────────
    news_items = [
        NewsItem(
            title="Tomato prices surge by 20% in Chennai wholesale market",
            description="Wholesale tomato prices jumped due to supply chain disruption in Karnataka. Retail prices expected to follow within days.",
            category="price_update",
            severity="warning",
            source_url="https://example.com/tomato-prices-surge",
            published_at=datetime.now() - timedelta(hours=2),
        ),
        NewsItem(
            title="Festival season demand expected to boost catering orders",
            description="Upcoming Pongal and temple festivals expected to increase demand for catering services by 30% in South Tamil Nadu.",
            category="demand_signal",
            severity="info",
            source_url="https://example.com/festival-demand",
            published_at=datetime.now() - timedelta(hours=5),
        ),
        NewsItem(
            title="LPG commercial cylinder price revised upward",
            description="Commercial LPG cylinder prices increased by ₹50 effective this month. Small food businesses may see margin pressure.",
            category="price_update",
            severity="warning",
            source_url="https://example.com/lpg-price-hike",
            published_at=datetime.now() - timedelta(hours=8),
        ),
    ]
    db.add_all(news_items)

    db.commit()
    db.close()
    print("Database seeded successfully!")


if __name__ == "__main__":
    seed_database()
