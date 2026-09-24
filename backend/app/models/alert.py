from sqlalchemy import Boolean, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AlertConfig(Base):
    __tablename__ = "alert_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    service: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    z_threshold: Mapped[float] = mapped_column(Float, default=3.0, server_default="3.0")
    slack_webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
