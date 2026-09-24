from fastapi import FastAPI

from app.api.routes import alerts, anomalies, config, costs, health, services
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.include_router(health.router, tags=["health"])
app.include_router(alerts.router, tags=["alerts"])
app.include_router(costs.router, tags=["costs"])
app.include_router(anomalies.router, tags=["anomalies"])
app.include_router(services.router, tags=["services"])
app.include_router(config.router, tags=["config"])


@app.get("/")
async def root():
    return {"service": settings.app_name, "environment": settings.environment}
