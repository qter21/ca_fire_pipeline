"""
Processing Checkpoint Models
Track processing state for pause/resume functionality
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ProcessingStage(str, Enum):
    """Processing stage enum"""
    STAGE1_ARCHITECTURE = "stage1_architecture"
    STAGE2_CONTENT = "stage2_content"
    STAGE3_MULTI_VERSION = "stage3_multi_version"
    RECONCILIATION = "reconciliation"
    COMPLETED = "completed"


class CheckpointStatus(str, Enum):
    """Checkpoint status"""
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingCheckpoint(BaseModel):
    """
    Model for tracking processing checkpoints
    Allows pause/resume of long-running processes
    """
    code: str
    stage: ProcessingStage
    status: CheckpointStatus = CheckpointStatus.IN_PROGRESS

    # Progress tracking
    total_sections: int = 0
    processed_sections: int = 0
    failed_sections: List[str] = Field(default_factory=list)

    # Batch tracking for Stage 2
    current_batch: int = 0
    total_batches: int = 0
    batch_size: int = 50

    # Timing
    started_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # Stage completion flags
    stage1_completed: bool = False
    stage2_completed: bool = False
    stage3_completed: bool = False
    reconciliation_completed: bool = False

    # Additional metadata
    workers: int = 15
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic config"""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CheckpointUpdate(BaseModel):
    """Model for updating checkpoint fields"""
    stage: Optional[ProcessingStage] = None
    status: Optional[CheckpointStatus] = None
    processed_sections: Optional[int] = None
    failed_sections: Optional[List[str]] = None
    current_batch: Optional[int] = None
    last_updated: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    stage1_completed: Optional[bool] = None
    stage2_completed: Optional[bool] = None
    stage3_completed: Optional[bool] = None
    reconciliation_completed: Optional[bool] = None
    error_message: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None

    class Config:
        """Pydantic config"""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
