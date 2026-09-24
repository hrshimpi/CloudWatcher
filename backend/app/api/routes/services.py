from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.billing import BillingRecord, DailyServiceCost
from app.schemas.costs import DailyCostPoint
from app.schemas.services import ServiceDrilldownResponse, SkuCostBreakdown

router = APIRouter()


@router.get("/services/{service}/drilldown", response_model=ServiceDrilldownResponse)
async def service_drilldown(
    service: str,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    top_n: int = Query(5, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(400, "start_date must not be after end_date")

    exists_result = await db.execute(
        select(DailyServiceCost.service).where(DailyServiceCost.service == service).limit(1)
    )
    if exists_result.scalar_one_or_none() is None:
        raise HTTPException(404, f"No cost data for service '{service}'")

    cost_filters = [DailyServiceCost.service == service]
    if start_date is not None:
        cost_filters.append(DailyServiceCost.date >= start_date)
    if end_date is not None:
        cost_filters.append(DailyServiceCost.date <= end_date)

    time_series_result = await db.execute(
        select(DailyServiceCost.date, DailyServiceCost.total_cost)
        .where(*cost_filters)
        .order_by(DailyServiceCost.date)
    )
    time_series = [DailyCostPoint(date=day, total_cost=cost) for day, cost in time_series_result.all()]
    total_cost = sum((point.total_cost for point in time_series), Decimal(0))

    sku_filters = [BillingRecord.service == service]
    if start_date is not None:
        sku_filters.append(BillingRecord.date >= start_date)
    if end_date is not None:
        sku_filters.append(BillingRecord.date <= end_date)

    top_skus_result = await db.execute(
        select(BillingRecord.sku, func.sum(BillingRecord.cost))
        .where(*sku_filters)
        .group_by(BillingRecord.sku)
        .order_by(func.sum(BillingRecord.cost).desc())
        .limit(top_n)
    )
    top_skus = [SkuCostBreakdown(sku=sku, total_cost=cost) for sku, cost in top_skus_result.all()]

    return ServiceDrilldownResponse(
        service=service,
        start_date=start_date,
        end_date=end_date,
        total_cost=total_cost,
        time_series=time_series,
        top_skus=top_skus,
    )
