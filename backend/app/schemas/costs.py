from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class DailyCostPoint(BaseModel):
    date: date
    total_cost: Decimal


class ServiceCostBreakdown(BaseModel):
    service: str
    total_cost: Decimal


class CostSummaryResponse(BaseModel):
    provider: str | None
    start_date: date | None
    end_date: date | None
    total_cost: Decimal
    by_service: list[ServiceCostBreakdown]
    trend: list[DailyCostPoint]
