from datetime import date as date_
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Float, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[int] = mapped_column(primary_key=True)
    service: Mapped[str] = mapped_column(String(100), index=True)
    date: Mapped[date_] = mapped_column(Date, index=True)
    expected_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    actual_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    z_score: Mapped[float] = mapped_column(Float)
    pct_deviation: Mapped[float] = mapped_column(Float)
    top_contributor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    root_cause_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open", server_default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
