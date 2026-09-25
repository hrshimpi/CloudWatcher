from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.anomaly import Anomaly
from app.schemas.anomalies import AnomalyResponse
from app.schemas.detection import DetectionRunResponse
from app.services.alerting import detect_and_alert

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


@router.post("/anomalies/detect", response_model=DetectionRunResponse)
async def trigger_detection(
    dry_run: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Runs anomaly detection for every service, then alerts on anything newly
    flagged. This is what Cloud Scheduler calls nightly; it's also safe to
    call manually (e.g. with `?dry_run=true` to see what it would do)."""
    settings = get_settings()
    effective_dry_run = settings.alerts_dry_run if dry_run is None else dry_run

    results = await detect_and_alert(db, dry_run=dry_run)

    return DetectionRunResponse(
        anomalies_processed=len(results),
        alerts_sent=sum(1 for r in results if r.sent),
        dry_run=effective_dry_run,
    )


@router.get("/anomalies/{anomaly_id}", response_model=AnomalyResponse)
async def get_anomaly(anomaly_id: int, db: AsyncSession = Depends(get_db)):
    anomaly = await db.get(Anomaly, anomaly_id)
    if anomaly is None:
        raise HTTPException(404, f"Anomaly {anomaly_id} not found")
    return anomaly
