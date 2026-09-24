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
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if status is not None:
        filters.append(Anomaly.status == status)
    if service is not None:
        filters.append(Anomaly.service == service)

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
