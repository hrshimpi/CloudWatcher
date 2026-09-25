from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def check_database(session: AsyncSession) -> bool:
    try:
        await session.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 -- a health check must not crash on ANY failure mode
        return False
