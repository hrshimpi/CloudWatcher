from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.costs import DailyCostPoint


class SkuCostBreakdown(BaseModel):
    sku: str
    total_cost: Decimal


class ServiceDrilldownResponse(BaseModel):
    service: str
    start_date: date | None
    end_date: date | None
    total_cost: Decimal
    time_series: list[DailyCostPoint]
    top_skus: list[SkuCostBreakdown]
