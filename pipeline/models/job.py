"""Job model for tracking pipeline jobs."""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job status enum."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(BaseModel):
    """Model for a pipeline job."""

    job_id: str = Field(..., description="Unique job identifier")
    code: str = Field(..., description="Code being processed")
    status: JobStatus = Field(JobStatus.PENDING, description="Current job status")
    stage: str = Field("not_started", description="Current stage (stage1, stage2, stage3)")

    # Progress tracking
    total_sections: int = Field(0, description="Total sections to process")
    processed_sections: int = Field(0, description="Sections processed so far")
    failed_sections: int = Field(0, description="Sections that failed")
    progress_percentage: float = Field(0.0, description="Progress percentage (0-100)")

    # Timing
    started_at: Optional[datetime] = Field(None, description="Job start time")
    finished_at: Optional[datetime] = Field(None, description="Job finish time")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")

    # Error tracking
    error_message: Optional[str] = Field(None, description="Error message if failed")
    failed_section_urls: list[str] = Field(default_factory=list, description="URLs of failed sections")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Job creation time")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update time")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "evid_20251008_120530",
                "code": "EVID",
                "status": "running",
                "stage": "stage2",
                "total_sections": 512,
                "processed_sections": 256,
                "progress_percentage": 50.0,
                "started_at": "2025-10-08T12:05:30Z"
            }
        }


class JobCreate(BaseModel):
    """Model for creating a new job."""

    code: str
    metadata: Optional[Dict[str, Any]] = None


class JobUpdate(BaseModel):
    """Model for updating a job."""

    status: Optional[JobStatus] = None
    stage: Optional[str] = None
    total_sections: Optional[int] = None
    processed_sections: Optional[int] = None
    failed_sections: Optional[int] = None
    progress_percentage: Optional[float] = None
    finished_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None
    failed_section_urls: Optional[list[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)
