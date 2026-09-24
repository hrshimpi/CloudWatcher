from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.alert import AlertConfig
from app.schemas.thresholds import AlertConfigResponse, AlertConfigUpsertRequest

router = APIRouter()


async def _get_config_by_exact_service(db: AsyncSession, service: str | None) -> AlertConfig | None:
    condition = AlertConfig.service.is_(None) if service is None else AlertConfig.service == service
    result = await db.execute(select(AlertConfig).where(condition))
    return result.scalar_one_or_none()


@router.get("/config/thresholds", response_model=list[AlertConfigResponse])
async def get_thresholds(service: str | None = Query(None), db: AsyncSession = Depends(get_db)):
    filters = []
    if service is not None:
        filters.append(AlertConfig.service == service)

    result = await db.execute(
        select(AlertConfig).where(*filters).order_by(AlertConfig.service.is_(None).desc(), AlertConfig.service)
    )
    return result.scalars().all()


@router.put("/config/thresholds", response_model=AlertConfigResponse)
async def upsert_threshold(payload: AlertConfigUpsertRequest, db: AsyncSession = Depends(get_db)):
    """Creates or updates the alert config for `service` (or the global
    default config, when `service` is omitted). `service` is the upsert key,
    not a patch target -- every other field is set to exactly what's given."""
    config = await _get_config_by_exact_service(db, payload.service)
    if config is None:
        config = AlertConfig(service=payload.service)
        db.add(config)

    config.z_threshold = payload.z_threshold
    config.slack_webhook_url = payload.slack_webhook_url
    config.enabled = payload.enabled

    await db.commit()
    await db.refresh(config)
    return config
