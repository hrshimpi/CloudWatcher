from pydantic import BaseModel, ConfigDict, Field


class AlertConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service: str | None
    z_threshold: float
    slack_webhook_url: str | None
    enabled: bool


class AlertConfigUpsertRequest(BaseModel):
    service: str | None = None
    z_threshold: float = Field(gt=0)
    slack_webhook_url: str | None = None
    enabled: bool = True
