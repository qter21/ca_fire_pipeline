"""
Failed Section Model
Track sections that failed during processing for later retry
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class FailureType(str, Enum):
    """Type of failure"""
    API_ERROR = "api_error"              # Firecrawl API errors
    TIMEOUT = "timeout"                   # Request timeout
    PARSE_ERROR = "parse_error"          # Content parsing failed
    EMPTY_CONTENT = "empty_content"      # No content found
    NETWORK_ERROR = "network_error"      # Network issues
    MULTI_VERSION_TIMEOUT = "multi_version_timeout"  # Playwright timeout
    REPEALED = "repealed"                # Section repealed/doesn't exist
    UNKNOWN = "unknown"                  # Unclassified error


class RetryStatus(str, Enum):
    """Retry status"""
    PENDING = "pending"           # Not yet retried
    RETRYING = "retrying"         # Currently being retried
    SUCCEEDED = "succeeded"       # Manual retry succeeded
    FAILED = "failed"             # Manual retry failed
    ABANDONED = "abandoned"       # Confirmed unretrievable (repealed, etc.)


class FailedSection(BaseModel):
    """
    Model for tracking failed section extractions
    Stores failure details for later manual retry
    """
    code: str
    section: str
    url: str

    # Failure details
    failure_type: FailureType
    error_message: str
    stack_trace: Optional[str] = None

    # Context
    stage: str  # "stage2_content" or "stage3_multi_version"
    batch_number: Optional[int] = None
    attempt_number: int = 1

    # Retry tracking
    retry_status: RetryStatus = RetryStatus.PENDING
    retry_count: int = 0
    last_retry_at: Optional[datetime] = None
    retry_attempts: List[Dict[str, Any]] = Field(default_factory=list)

    # Timing
    failed_at: datetime = Field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None

    # Additional metadata
    is_multi_version: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None

    class Config:
        """Pydantic config"""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FailedSectionUpdate(BaseModel):
    """Model for updating failed section fields"""
    retry_status: Optional[RetryStatus] = None
    retry_count: Optional[int] = None
    last_retry_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    error_message: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        """Pydantic config"""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FailureReport(BaseModel):
    """
    Comprehensive failure report for a code
    Generated at end of processing
    """
    code: str
    generated_at: datetime = Field(default_factory=datetime.now)

    # Overall stats
    total_sections: int
    successful_sections: int
    failed_sections: int
    completion_rate: float

    # Failure breakdown
    failures_by_type: Dict[str, int] = Field(default_factory=dict)
    failures_by_stage: Dict[str, int] = Field(default_factory=dict)

    # Failed section details
    failed_section_list: List[Dict[str, Any]] = Field(default_factory=list)

    # Retry stats
    pending_retry: int = 0
    retry_succeeded: int = 0
    retry_failed: int = 0
    abandoned: int = 0

    # Processing metadata
    duration_seconds: Optional[float] = None
    processing_rate: Optional[float] = None  # sections per second

    class Config:
        """Pydantic config"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
