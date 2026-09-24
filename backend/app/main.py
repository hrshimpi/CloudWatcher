from fastapi import FastAPI

from app.api.routes import alerts, health
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.include_router(health.router, tags=["health"])
app.include_router(alerts.router, tags=["alerts"])


@app.get("/")
async def root():
    return {"service": settings.app_name, "environment": settings.environment}
