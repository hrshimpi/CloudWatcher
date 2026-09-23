from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.health_service import check_database

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    db_ok = await check_database(db)

    return {
        "status": "ok" if db_ok else "degraded",
        "database": "up" if db_ok else "down",
    }
