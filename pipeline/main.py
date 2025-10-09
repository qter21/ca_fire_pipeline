"""Main FastAPI application for CA Fire Pipeline."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pipeline.core.config import get_settings
from pipeline.core.database import get_db_manager, close_db_manager
from pipeline.routers import health, crawler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events.

    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("Starting CA Fire Pipeline API")
    settings = get_settings()
    logger.info(f"Configuration loaded: API_PORT={settings.API_PORT}")

    # Initialize database connection
    try:
        db = get_db_manager()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down CA Fire Pipeline API")
    close_db_manager()
    logger.info("Database connection closed")


# Create FastAPI app
app = FastAPI(
    title="CA Fire Pipeline API",
    description="Firecrawl-based data pipeline for California legal codes",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(crawler.router)


@app.get("/")
async def root():
    """Root endpoint.

    Returns:
        API information
    """
    return {
        "name": "CA Fire Pipeline API",
        "version": "2.0.0",
        "description": "Firecrawl-based data pipeline for California legal codes",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "crawler": "/api/v2/crawler"
        }
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "pipeline.main:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        reload=True
    )
