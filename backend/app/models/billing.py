from datetime import date as date_
from decimal import Decimal

from sqlalchemy import Date, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BillingRecord(Base):
    __tablename__ = "billing_records"
    __table_args__ = (
        # Every real query against this table filters by service (+ an
        # optional date range) -- see app/api/routes/services.py and
        # app/services/anomaly_detection.py's top-contributor lookup. A
        # composite index serves that directly, and standalone `service`
        # (via its leftmost prefix) and `date` indexes become redundant, so
        # those single-column indexes were dropped in favor of this one.
        Index("ix_billing_records_service_date", "service", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(50), index=True)
    account_id: Mapped[str] = mapped_column(String(100), index=True)
    service: Mapped[str] = mapped_column(String(100))
    sku: Mapped[str] = mapped_column(String(255))
    date: Mapped[date_] = mapped_column(Date)
    cost: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    currency: Mapped[str] = mapped_column(String(3), default="USD")


class DailyServiceCost(Base):
    __tablename__ = "daily_service_costs"
    __table_args__ = (
        # The primary key is (date, provider, service) -- good for the
        # provider/date-range filters in costs/summary, but the drilldown
        # endpoint's "one service, optional date range" lookup can't use a
        # date-leading index via its leftmost prefix. This serves that
        # pattern directly instead of falling back to a full scan.
        Index("ix_daily_service_costs_service_date", "service", "date"),
    )

    date: Mapped[date_] = mapped_column(Date, primary_key=True)
    provider: Mapped[str] = mapped_column(String(50), primary_key=True)
    service: Mapped[str] = mapped_column(String(100), primary_key=True)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4))
