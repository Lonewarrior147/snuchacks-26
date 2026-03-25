from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    Text,
    Float,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from database.connection import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    email = Column(Text, unique=True, nullable=False)
    phone = Column(Text, nullable=True)
    password_hash = Column(Text, nullable=False)
    language = Column(Text, default="en")
    business_name = Column(Text, default="")
    business_type = Column(Text, default="tiffin")
    bank_balance = Column(Float, default=0)
    petty_cash = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="user")
    payables = relationship("Payable", back_populates="user")
    receivables = relationship("Receivable", back_populates="user")
    daily_expenses = relationship("DailyExpense", back_populates="user")
    insights = relationship("InsightCache", back_populates="user")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    counterparty_name = Column(Text, nullable=False)
    transaction_type = Column(Text, nullable=False)  # 'credit' or 'debit'
    amount = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")


class Payable(Base):
    __tablename__ = "payables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(Text, nullable=False)
    amount = Column(Float, nullable=False)
    due_date = Column(Date, nullable=False)
    category = Column(Text, nullable=True)  # vendor/salary/rent/utility/subscription/emi
    penalty_risk = Column(Integer, default=50)
    operational_importance = Column(Integer, default=50)
    flexibility = Column(Integer, default=50)
    is_recurring = Column(Boolean, default=False)
    recurrence_interval = Column(Text, nullable=True)  # daily/weekly/monthly
    status = Column(Text, default="pending")  # pending/paid/delayed
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="payables")


class Receivable(Base):
    __tablename__ = "receivables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source = Column(Text, nullable=False)
    amount = Column(Float, nullable=False)
    expected_date = Column(Date, nullable=False)
    confidence = Column(Float, default=0.8)
    status = Column(Text, default="pending")  # pending/received/overdue
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="receivables")


class DailyExpense(Base):
    __tablename__ = "daily_expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    description = Column(Text, nullable=False)
    amount = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="daily_expenses")


class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(Text, nullable=False)  # price_update/demand_signal/festival_alert/market_trend
    severity = Column(Text, default="info")  # info/warning/critical
    source_url = Column(Text, unique=True, nullable=True)
    published_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)


class InsightCache(Base):
    __tablename__ = "insights_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    insight_type = Column(Text, nullable=False)  # action/warning/opportunity/critical
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(Text, default="moderate")  # urgent/moderate/low
    potential_savings = Column(Float, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="insights")
