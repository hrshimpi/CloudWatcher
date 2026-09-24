from dataclasses import asdict

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.alerting import send_test_alert

router = APIRouter()


class TestAlertRequest(BaseModel):
    service: str | None = None
    slack_webhook_url: str | None = None
    dry_run: bool | None = None


@router.post("/alerts/test")
async def test_alert(payload: TestAlertRequest, db: AsyncSession = Depends(get_db)):
    """Sends (or logs, in dry-run) a Slack message built from example numbers,
    through the same LLM-explanation + formatting pipeline real alerts use.

    Uses `slack_webhook_url` if given, otherwise looks up alert_config for
    `service` (falling back to the global default config).
    """
    result = await send_test_alert(
        db,
        service=payload.service,
        slack_webhook_url=payload.slack_webhook_url,
        dry_run=payload.dry_run,
    )
    return asdict(result)
