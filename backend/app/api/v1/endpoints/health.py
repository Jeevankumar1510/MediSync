import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.config import settings
from app.database import get_db

router = APIRouter()
logger = logging.getLogger("medisync.health")


@router.get(
    "/health",
    summary="System Health & Diagnostic Check",
    description="Validates API availability, PostgreSQL connection, pgvector extension, and Redis connectivity.",
    status_code=status.HTTP_200_OK,
)
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    health_status: Dict[str, Any] = {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
        "checks": {
            "database": "unknown",
            "pgvector": "unknown",
            "redis": "unknown",
        }
    }
    all_healthy = True

    # 1. Database Check
    try:
        db_res = await db.execute(text("SELECT 1"))
        if db_res.scalar() == 1:
            health_status["checks"]["database"] = "connected"
    except Exception as exc:
        health_status["checks"]["database"] = f"error: {str(exc)}"
        all_healthy = False
        logger.error(f"Health check failed on database query: {exc}")

    # 2. pgvector Extension Check
    try:
        ext_res = await db.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector';"))
        vector_installed = ext_res.scalar()
        if vector_installed:
            health_status["checks"]["pgvector"] = "installed"
        else:
            health_status["checks"]["pgvector"] = "not_found"
            all_healthy = False
    except Exception as exc:
        health_status["checks"]["pgvector"] = f"error: {str(exc)}"
        all_healthy = False
        logger.error(f"Health check failed on pgvector verification: {exc}")

    # 3. Redis Check
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        pong = await r.ping()
        await r.close()
        if pong:
            health_status["checks"]["redis"] = "connected"
    except Exception as exc:
        health_status["checks"]["redis"] = f"unavailable: {str(exc)}"
        # Note: Redis might be optional in early minimal testing, but we flag it
        logger.warning(f"Health check warning on Redis: {exc}")

    if not all_healthy:
        health_status["status"] = "degraded"
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=health_status)

    return health_status

