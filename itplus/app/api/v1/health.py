"""Health check with DB and Redis status."""

import redis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from itplus.app.core.config import get_settings
from itplus.app.core.database import get_db

router = APIRouter()


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    settings = get_settings()
    status_info = {
        "status": "ok",
        "service": settings.app_name,
        "checks": {
            "database": "unknown",
            "redis": "unknown",
        },
    }

    try:
        db.execute(text("SELECT 1"))
        status_info["checks"]["database"] = "ok"
    except Exception as exc:
        status_info["status"] = "degraded"
        status_info["checks"]["database"] = f"error: {exc}"

    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
        status_info["checks"]["redis"] = "ok"
    except Exception as exc:
        status_info["status"] = "degraded"
        status_info["checks"]["redis"] = f"error: {exc}"

    return status_info
