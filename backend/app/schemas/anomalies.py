from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AnomalyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service: str
    date: date
    expected_cost: Decimal
    actual_cost: Decimal
    z_score: float
    pct_deviation: float
    top_contributor: str | None
    root_cause_explanation: str | None
    status: str
    created_at: datetime
