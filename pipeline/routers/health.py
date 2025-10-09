"""Health check endpoint."""

import logging
from fastapi import APIRouter, HTTPException
from datetime import datetime

from pipeline.core.database import get_db_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint.

    Returns:
        Dictionary with service health status
    """
    try:
        # Check database connection
        db = get_db_manager()
        db.client.admin.command("ping")

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "service": "ca-fire-pipeline"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
