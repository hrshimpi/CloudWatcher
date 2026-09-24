from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.billing import DailyServiceCost
from app.schemas.costs import CostSummaryResponse, DailyCostPoint, ServiceCostBreakdown

router = APIRouter()


@router.get("/costs/summary", response_model=CostSummaryResponse)
async def cost_summary(
    provider: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(400, "start_date must not be after end_date")

    filters = []
    if provider is not None:
        filters.append(DailyServiceCost.provider == provider)
    if start_date is not None:
        filters.append(DailyServiceCost.date >= start_date)
    if end_date is not None:
        filters.append(DailyServiceCost.date <= end_date)

    total_result = await db.execute(select(func.sum(DailyServiceCost.total_cost)).where(*filters))
    total_cost = total_result.scalar() or 0

    by_service_result = await db.execute(
        select(DailyServiceCost.service, func.sum(DailyServiceCost.total_cost))
        .where(*filters)
        .group_by(DailyServiceCost.service)
        .order_by(func.sum(DailyServiceCost.total_cost).desc())
    )
    by_service = [
        ServiceCostBreakdown(service=service, total_cost=cost) for service, cost in by_service_result.all()
    ]

    trend_result = await db.execute(
        select(DailyServiceCost.date, func.sum(DailyServiceCost.total_cost))
        .where(*filters)
        .group_by(DailyServiceCost.date)
        .order_by(DailyServiceCost.date)
    )
    trend = [DailyCostPoint(date=day, total_cost=cost) for day, cost in trend_result.all()]

    return CostSummaryResponse(
        provider=provider,
        start_date=start_date,
        end_date=end_date,
        total_cost=total_cost,
        by_service=by_service,
        trend=trend,
    )
