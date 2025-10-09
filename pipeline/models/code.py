"""Code model for California legal codes."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Code(BaseModel):
    """Model for a California legal code."""

    code: str = Field(..., description="Code abbreviation (e.g., 'FAM', 'PEN')")
    full_name: Optional[str] = Field(None, description="Full code name (e.g., 'Family Code')")
    url: str = Field(..., description="Architecture page URL")

    # Statistics
    total_sections: int = Field(0, description="Total number of sections")
    single_version_count: int = Field(0, description="Number of single-version sections")
    multi_version_count: int = Field(0, description="Number of multi-version sections")
    processed_sections: int = Field(0, description="Number of sections processed")

    # Status
    stage1_completed: bool = Field(False, description="Architecture crawling completed")
    stage2_completed: bool = Field(False, description="Content extraction completed")
    stage3_completed: bool = Field(False, description="Multi-version extraction completed")

    # Timestamps
    stage1_started: Optional[datetime] = Field(None, description="Stage 1 start time")
    stage1_finished: Optional[datetime] = Field(None, description="Stage 1 finish time")
    stage2_started: Optional[datetime] = Field(None, description="Stage 2 start time")
    stage2_finished: Optional[datetime] = Field(None, description="Stage 2 finish time")
    stage3_started: Optional[datetime] = Field(None, description="Stage 3 start time")
    stage3_finished: Optional[datetime] = Field(None, description="Stage 3 finish time")

    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "EVID",
                "full_name": "Evidence Code",
                "url": "https://leginfo.legislature.ca.gov/faces/codes_displayexpandedbranch.xhtml?tocCode=EVID",
                "total_sections": 512,
                "single_version_count": 510,
                "multi_version_count": 2,
                "stage1_completed": True,
                "stage2_completed": False
            }
        }


class CodeCreate(BaseModel):
    """Model for creating a new code entry."""

    code: str
    full_name: Optional[str] = None
    url: str


class CodeUpdate(BaseModel):
    """Model for updating code metadata."""

    full_name: Optional[str] = None
    total_sections: Optional[int] = None
    single_version_count: Optional[int] = None
    multi_version_count: Optional[int] = None
    processed_sections: Optional[int] = None
    stage1_completed: Optional[bool] = None
    stage2_completed: Optional[bool] = None
    stage3_completed: Optional[bool] = None
    stage1_started: Optional[datetime] = None
    stage1_finished: Optional[datetime] = None
    stage2_started: Optional[datetime] = None
    stage2_finished: Optional[datetime] = None
    stage3_started: Optional[datetime] = None
    stage3_finished: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)
