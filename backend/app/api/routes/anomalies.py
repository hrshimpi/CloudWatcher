from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.anomaly import Anomaly
from app.schemas.anomalies import AnomalyResponse

router = APIRouter()


@router.get("/anomalies", response_model=list[AnomalyResponse])
async def list_anomalies(
    status: str | None = Query(None),
    service: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(400, "start_date must not be after end_date")

    filters = []
    if status is not None:
        filters.append(Anomaly.status == status)
    if service is not None:
        filters.append(Anomaly.service == service)
    if start_date is not None:
        filters.append(Anomaly.date >= start_date)
    if end_date is not None:
        filters.append(Anomaly.date <= end_date)

    result = await db.execute(
        select(Anomaly)
        .where(*filters)
        .order_by(Anomaly.date.desc(), Anomaly.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.get("/anomalies/{anomaly_id}", response_model=AnomalyResponse)
async def get_anomaly(anomaly_id: int, db: AsyncSession = Depends(get_db)):
    anomaly = await db.get(Anomaly, anomaly_id)
    if anomaly is None:
        raise HTTPException(404, f"Anomaly {anomaly_id} not found")
    return anomaly
