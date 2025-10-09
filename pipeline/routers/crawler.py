"""Crawler API endpoints."""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from pipeline.core.database import get_db_manager
from pipeline.services.architecture_crawler import ArchitectureCrawler
from pipeline.services.content_extractor import ContentExtractor
from pipeline.services.firecrawl_service import FirecrawlService
from pipeline.models.job import JobCreate, JobUpdate, JobStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/crawler", tags=["crawler"])


# ==================== Request/Response Models ====================


class StartCrawlerRequest(BaseModel):
    """Request model for starting a crawler job."""

    code: str
    skip_multi_version: bool = False


class StageResponse(BaseModel):
    """Response model for stage completion."""

    code: str
    stage: str
    success: bool
    message: str
    total_sections: Optional[int] = None
    single_version_count: Optional[int] = None
    multi_version_count: Optional[int] = None
    failed_sections: Optional[list] = None


class JobResponse(BaseModel):
    """Response model for job creation."""

    job_id: str
    code: str
    status: str
    message: str


# ==================== Background Tasks ====================


def run_full_pipeline(job_id: str, code: str, skip_multi_version: bool = False):
    """Run the full pipeline in the background.

    Args:
        job_id: Job identifier
        code: Code abbreviation
        skip_multi_version: Whether to skip multi-version extraction
    """
    db = get_db_manager()
    firecrawl = FirecrawlService()

    try:
        # Update job status to running
        db.update_job(job_id, JobUpdate(status=JobStatus.RUNNING, stage="stage1"))

        # Stage 1: Architecture crawling
        logger.info(f"[Job {job_id}] Starting Stage 1")
        crawler = ArchitectureCrawler(firecrawl_service=firecrawl, db_manager=db)
        stage1_result = crawler.crawl(code, save_to_db=True)

        db.update_job(
            job_id,
            JobUpdate(
                stage="stage2",
                total_sections=stage1_result["total_sections"]
            )
        )

        # Stage 2: Content extraction
        logger.info(f"[Job {job_id}] Starting Stage 2")
        extractor = ContentExtractor(firecrawl_service=firecrawl, db_manager=db)

        def progress_callback(processed, total):
            percentage = (processed / total * 100) if total > 0 else 0
            db.update_job(
                job_id,
                JobUpdate(
                    processed_sections=processed,
                    progress_percentage=percentage
                )
            )

        stage2_result = extractor.extract(
            code,
            skip_multi_version=skip_multi_version,
            progress_callback=progress_callback
        )

        # Stage 3: Multi-version extraction (if not skipped)
        if not skip_multi_version and stage2_result["multi_version_count"] > 0:
            logger.info(f"[Job {job_id}] Starting Stage 3")
            db.update_job(job_id, JobUpdate(stage="stage3"))

            stage3_result = extractor.extract_multi_version_sections(
                code,
                progress_callback=lambda p, t: db.update_job(
                    job_id,
                    JobUpdate(processed_sections=stage2_result["single_version_count"] + p)
                )
            )
        else:
            logger.info(f"[Job {job_id}] Skipping Stage 3 (no multi-version sections or skipped)")

        # Mark job as completed
        db.update_job(
            job_id,
            JobUpdate(
                status=JobStatus.COMPLETED,
                stage="completed",
                progress_percentage=100.0
            )
        )

        logger.info(f"[Job {job_id}] Pipeline completed successfully")

    except Exception as e:
        logger.error(f"[Job {job_id}] Pipeline failed: {e}")
        db.update_job(
            job_id,
            JobUpdate(
                status=JobStatus.FAILED,
                error_message=str(e)
            )
        )


# ==================== Endpoints ====================


@router.post("/start/{code}", response_model=JobResponse)
async def start_crawler(
    code: str,
    background_tasks: BackgroundTasks,
    skip_multi_version: bool = False
):
    """Start the full pipeline for a code (Stage 1 + 2 + 3).

    Args:
        code: Code abbreviation (e.g., 'EVID', 'FAM')
        skip_multi_version: Skip multi-version extraction (Stage 3)

    Returns:
        Job information with job_id for tracking
    """
    try:
        db = get_db_manager()

        # Create job
        job_create = JobCreate(
            code=code.upper(),
            metadata={"skip_multi_version": skip_multi_version}
        )
        job = db.create_job(job_create)

        # Start pipeline in background
        background_tasks.add_task(
            run_full_pipeline,
            job.job_id,
            code.upper(),
            skip_multi_version
        )

        logger.info(f"Started pipeline job {job.job_id} for code {code}")

        return JobResponse(
            job_id=job.job_id,
            code=code.upper(),
            status="started",
            message=f"Pipeline started for code {code}"
        )

    except Exception as e:
        logger.error(f"Failed to start crawler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of a running or completed job.

    Args:
        job_id: Job identifier

    Returns:
        Job status information
    """
    try:
        db = get_db_manager()
        job = db.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        return job

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stage1/{code}", response_model=StageResponse)
async def run_stage1(code: str):
    """Run Stage 1 (architecture crawling) for a code.

    Args:
        code: Code abbreviation

    Returns:
        Stage 1 results
    """
    try:
        db = get_db_manager()
        firecrawl = FirecrawlService()
        crawler = ArchitectureCrawler(firecrawl_service=firecrawl, db_manager=db)

        result = crawler.crawl(code.upper(), save_to_db=True)

        return StageResponse(
            code=code.upper(),
            stage="stage1",
            success=True,
            message=f"Stage 1 completed: {result['total_sections']} sections found",
            total_sections=result["total_sections"]
        )

    except Exception as e:
        logger.error(f"Stage 1 failed for {code}: {e}")
        return StageResponse(
            code=code.upper(),
            stage="stage1",
            success=False,
            message=f"Stage 1 failed: {str(e)}"
        )


@router.post("/stage2/{code}", response_model=StageResponse)
async def run_stage2(code: str, skip_multi_version: bool = False):
    """Run Stage 2 (content extraction) for a code.

    Args:
        code: Code abbreviation
        skip_multi_version: Skip multi-version sections

    Returns:
        Stage 2 results
    """
    try:
        db = get_db_manager()
        firecrawl = FirecrawlService()
        extractor = ContentExtractor(firecrawl_service=firecrawl, db_manager=db)

        result = extractor.extract(code.upper(), skip_multi_version=skip_multi_version)

        return StageResponse(
            code=code.upper(),
            stage="stage2",
            success=True,
            message=f"Stage 2 completed: {result['single_version_count']} single-version, {result['multi_version_count']} multi-version",
            total_sections=result["total_sections"],
            single_version_count=result["single_version_count"],
            multi_version_count=result["multi_version_count"],
            failed_sections=result["failed_sections"]
        )

    except Exception as e:
        logger.error(f"Stage 2 failed for {code}: {e}")
        return StageResponse(
            code=code.upper(),
            stage="stage2",
            success=False,
            message=f"Stage 2 failed: {str(e)}"
        )


@router.post("/stage3/{code}", response_model=StageResponse)
async def run_stage3(code: str):
    """Run Stage 3 (multi-version extraction) for a code.

    Args:
        code: Code abbreviation

    Returns:
        Stage 3 results
    """
    try:
        db = get_db_manager()
        firecrawl = FirecrawlService()
        extractor = ContentExtractor(firecrawl_service=firecrawl, db_manager=db)

        result = extractor.extract_multi_version_sections(code.upper())

        return StageResponse(
            code=code.upper(),
            stage="stage3",
            success=True,
            message=f"Stage 3 completed: {result['extracted_count']}/{result['total_sections']} extracted",
            total_sections=result["total_sections"],
            failed_sections=result["failed_sections"]
        )

    except Exception as e:
        logger.error(f"Stage 3 failed for {code}: {e}")
        return StageResponse(
            code=code.upper(),
            stage="stage3",
            success=False,
            message=f"Stage 3 failed: {str(e)}"
        )


@router.get("/codes")
async def list_codes():
    """Get list of all codes in the database.

    Returns:
        List of code metadata
    """
    try:
        db = get_db_manager()
        codes = db.get_all_codes()
        return {"codes": codes}

    except Exception as e:
        logger.error(f"Failed to list codes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/recent")
async def get_recent_jobs(limit: int = 10):
    """Get recent jobs.

    Args:
        limit: Maximum number of jobs to return

    Returns:
        List of recent jobs
    """
    try:
        db = get_db_manager()
        jobs = db.get_recent_jobs(limit=limit)
        return {"jobs": jobs}

    except Exception as e:
        logger.error(f"Failed to get recent jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
