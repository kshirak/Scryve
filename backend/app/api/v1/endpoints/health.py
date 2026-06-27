"""Health-check endpoints used by orchestrators and uptime monitors."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import __version__
from app.config import settings
from app.core.logging import get_logger
from app.dependencies import get_db_session
from app.schemas.common import HealthStatus

router = APIRouter(tags=["Health"])
logger = get_logger(__name__)


@router.get(
    "/health",
    response_model=HealthStatus,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
)
async def health() -> HealthStatus:
    """Return basic service liveness information.

    Returns:
        A `HealthStatus` payload indicating the service is up.
    """
    return HealthStatus(
        status="ok",
        service=settings.app_name,
        version=__version__,
        environment=settings.app_env,
    )


@router.get(
    "/health/db",
    response_model=HealthStatus,
    status_code=status.HTTP_200_OK,
    summary="Readiness probe (verifies database connectivity)",
)
async def health_db(db: Session = Depends(get_db_session)) -> HealthStatus:
    """Check database connectivity by executing a trivial query.

    Args:
        db: Injected SQLAlchemy session.

    Returns:
        A `HealthStatus` payload reporting database connectivity.
    """
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except SQLAlchemyError:
        logger.exception("health.db.failed")
        db_status = "degraded"

    return HealthStatus(
        status=db_status,
        service=f"{settings.app_name} (db)",
        version=__version__,
        environment=settings.app_env,
    )
