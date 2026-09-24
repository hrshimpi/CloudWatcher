from datetime import date as date_
from decimal import Decimal

from sqlalchemy import Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BillingRecord(Base):
    __tablename__ = "billing_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(50), index=True)
    account_id: Mapped[str] = mapped_column(String(100), index=True)
    service: Mapped[str] = mapped_column(String(100), index=True)
    sku: Mapped[str] = mapped_column(String(255))
    date: Mapped[date_] = mapped_column(Date, index=True)
    cost: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    currency: Mapped[str] = mapped_column(String(3), default="USD")


class DailyServiceCost(Base):
    __tablename__ = "daily_service_costs"

    date: Mapped[date_] = mapped_column(Date, primary_key=True)
    provider: Mapped[str] = mapped_column(String(50), primary_key=True)
    service: Mapped[str] = mapped_column(String(100), primary_key=True)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4))
