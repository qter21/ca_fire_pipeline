"""Section model for California legal code sections."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Version(BaseModel):
    """Model for a single version of a multi-version section."""

    operative_date: Optional[str] = Field(None, description="Operative date (e.g., 'January 1, 2025')")
    content: Optional[str] = Field(None, description="Full text content of this version")
    legislative_history: Optional[str] = Field(None, description="Legislative history for this version")
    status: str = Field("current", description="Status: current, future, or historical")
    url: Optional[str] = Field(None, description="URL for this specific version")


class Section(BaseModel):
    """Model for a California legal code section (compatible with old pipeline)."""

    code: str = Field(..., description="Code abbreviation (e.g., 'FAM', 'PEN')")
    section: str = Field(..., description="Section number (e.g., '3044', '73d')")

    # Content fields
    content: Optional[str] = Field(None, description="Cleaned section content")
    raw_content: Optional[str] = Field(None, description="Raw content before cleaning")
    has_content: bool = Field(False, description="Whether content was successfully extracted")
    content_cleaned: bool = Field(False, description="Whether content has been cleaned")
    content_length: Optional[int] = Field(None, description="Length of content")
    raw_content_length: Optional[int] = Field(None, description="Length of raw content")

    # Legislative history fields
    legislative_history: Optional[str] = Field(None, description="Cleaned legislative history")
    raw_legislative_history: Optional[str] = Field(None, description="Raw legislative history")
    has_legislative_history: bool = Field(False, description="Whether legislative history exists")

    # Multi-version fields
    is_multi_version: bool = Field(False, description="Whether section has multiple versions")
    version_number: Optional[int] = Field(1, description="Version number for multi-version sections")
    versions: Optional[List[Version]] = Field(None, description="List of versions (for multi-version sections)")
    description: Optional[str] = Field(None, description="Version description (e.g., 'Amended by Stats. 2024...')")
    operative_date: Optional[str] = Field(None, description="Operative date for this version")
    is_current: bool = Field(True, description="Whether this is the current version")

    # Hierarchy information
    division: Optional[str] = Field(None, description="Division name")
    part: Optional[str] = Field(None, description="Part name")
    chapter: Optional[str] = Field(None, description="Chapter name")
    article: Optional[str] = Field(None, description="Article name")

    # Metadata
    url: str = Field(..., description="Source URL")
    metadata: Optional[Dict] = Field(None, description="Additional metadata")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "FAM",
                "section": "3044",
                "is_multi_version": True,
                "versions": [
                    {
                        "operative_date": "January 1, 2025",
                        "content": "(a) Upon a finding by the court...",
                        "legislative_history": "Amended by Stats. 2024, Ch. 544, Sec. 6.",
                        "status": "current"
                    }
                ],
                "division": "Division 10",
                "part": "Part 5",
                "chapter": "Chapter 5",
                "url": "https://leginfo.legislature.ca.gov/..."
            }
        }


class SectionCreate(BaseModel):
    """Model for creating a new section."""

    code: str
    section: str
    content: Optional[str] = None
    legislative_history: Optional[str] = None
    is_multi_version: bool = False
    versions: Optional[List[Version]] = None
    division: Optional[str] = None
    part: Optional[str] = None
    chapter: Optional[str] = None
    article: Optional[str] = None
    url: str


class SectionUpdate(BaseModel):
    """Model for updating an existing section."""

    # Content fields
    content: Optional[str] = None
    raw_content: Optional[str] = None
    has_content: Optional[bool] = None
    content_cleaned: Optional[bool] = None
    content_length: Optional[int] = None
    raw_content_length: Optional[int] = None

    # Legislative history fields
    legislative_history: Optional[str] = None
    raw_legislative_history: Optional[str] = None
    has_legislative_history: Optional[bool] = None

    # Multi-version fields
    is_multi_version: Optional[bool] = None
    version_number: Optional[int] = None
    versions: Optional[List[Version]] = None
    description: Optional[str] = None
    operative_date: Optional[str] = None
    is_current: Optional[bool] = None

    # Hierarchy
    division: Optional[str] = None
    part: Optional[str] = None
    chapter: Optional[str] = None
    article: Optional[str] = None

    # Metadata
    url: Optional[str] = None
    metadata: Optional[Dict] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
