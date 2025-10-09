"""Database connection and CRUD operations for MongoDB."""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pymongo import MongoClient, UpdateOne
from pymongo.database import Database
from pymongo.collection import Collection

from pipeline.core.config import get_settings
from pipeline.models.section import Section, SectionCreate, SectionUpdate
from pipeline.models.code import Code, CodeCreate, CodeUpdate
from pipeline.models.job import Job, JobCreate, JobUpdate, JobStatus

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manager for MongoDB database operations."""

    def __init__(self, mongodb_uri: Optional[str] = None):
        """Initialize database connection.

        Args:
            mongodb_uri: MongoDB connection URI (optional, will use config if not provided)
        """
        settings = get_settings()
        self.uri = mongodb_uri or settings.mongodb_uri
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None

    def connect(self) -> None:
        """Establish connection to MongoDB."""
        try:
            self.client = MongoClient(self.uri)
            # Extract database name from URI or use default
            db_name = self.uri.split("/")[-1].split("?")[0] or "ca_codes_db"
            self.db = self.client[db_name]

            # Test connection
            self.client.admin.command("ping")
            logger.info(f"Connected to MongoDB: {db_name}")

            # Create indexes
            self._create_indexes()

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    def _create_indexes(self) -> None:
        """Create database indexes for optimal query performance."""
        if self.db is None:
            return

        try:
            # section_contents collection indexes (using old pipeline name)
            # Note: Old pipeline may have duplicates, so skip unique index
            section_contents = self.db.section_contents
            section_contents.create_index([("code", 1), ("section", 1)])  # Non-unique to handle old data
            section_contents.create_index([("is_multi_version", 1)])
            section_contents.create_index([("updated_at", -1)])

            # code_architectures collection indexes (using old pipeline name)
            code_architectures = self.db.code_architectures
            code_architectures.create_index([("code", 1)])  # Non-unique for safety

            # Jobs collection indexes (new for this pipeline)
            jobs = self.db.jobs
            jobs.create_index([("job_id", 1)], unique=True)
            jobs.create_index([("status", 1)])
            jobs.create_index([("created_at", -1)])

            logger.info("Database indexes created")
        except Exception as e:
            logger.warning(f"Index creation warning (may already exist): {e}")

    @property
    def sections(self) -> Collection:
        """Get sections collection (using old pipeline name for compatibility)."""
        return self.db.section_contents

    @property
    def section_contents(self) -> Collection:
        """Get section_contents collection (alias for compatibility)."""
        return self.db.section_contents

    @property
    def codes(self) -> Collection:
        """Get codes collection (using old pipeline name for compatibility)."""
        return self.db.code_architectures

    @property
    def code_architectures(self) -> Collection:
        """Get code_architectures collection (alias for compatibility)."""
        return self.db.code_architectures

    @property
    def jobs(self) -> Collection:
        """Get jobs collection."""
        return self.db.jobs

    @property
    def processing_status(self) -> Collection:
        """Get processing_status collection (for compatibility with old pipeline)."""
        return self.db.processing_status

    # ==================== Section CRUD Operations ====================

    def create_section(self, section: SectionCreate) -> Section:
        """Create a new section.

        Args:
            section: Section data to create

        Returns:
            Created section with timestamps
        """
        section_dict = section.model_dump()
        section_dict["created_at"] = datetime.utcnow()
        section_dict["last_updated"] = datetime.utcnow()

        self.sections.insert_one(section_dict)
        logger.debug(f"Created section: {section.code} §{section.section}")

        return Section(**section_dict)

    def get_section(self, code: str, section: str) -> Optional[Section]:
        """Get a section by code and section number.

        Args:
            code: Code abbreviation (e.g., 'FAM')
            section: Section number (e.g., '3044')

        Returns:
            Section if found, None otherwise
        """
        doc = self.sections.find_one({"code": code, "section": section})
        if doc:
            doc.pop("_id", None)
            return Section(**doc)
        return None

    def update_section(self, code: str, section: str, update: SectionUpdate) -> Optional[Section]:
        """Update an existing section.

        Args:
            code: Code abbreviation
            section: Section number
            update: Update data

        Returns:
            Updated section if found, None otherwise
        """
        update_dict = {k: v for k, v in update.model_dump().items() if v is not None}
        update_dict["last_updated"] = datetime.utcnow()

        result = self.sections.find_one_and_update(
            {"code": code, "section": section},
            {"$set": update_dict},
            return_document=True
        )

        if result:
            result.pop("_id", None)
            logger.debug(f"Updated section: {code} §{section}")
            return Section(**result)
        return None

    def upsert_section(self, section: SectionCreate) -> Section:
        """Insert or update a section.

        Args:
            section: Section data

        Returns:
            Created or updated section
        """
        existing = self.get_section(section.code, section.section)

        if existing:
            # Update existing
            update = SectionUpdate(**section.model_dump(exclude={"code", "section"}))
            return self.update_section(section.code, section.section, update)
        else:
            # Create new
            return self.create_section(section)

    def get_sections_by_code(self, code: str, skip: int = 0, limit: int = 100) -> List[Section]:
        """Get all sections for a code.

        Args:
            code: Code abbreviation
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of sections
        """
        cursor = self.sections.find({"code": code}).skip(skip).limit(limit)
        sections = []
        for doc in cursor:
            doc.pop("_id", None)
            sections.append(Section(**doc))
        return sections

    def get_multi_version_sections(self, code: Optional[str] = None) -> List[Section]:
        """Get all multi-version sections, optionally filtered by code.

        Args:
            code: Optional code filter

        Returns:
            List of multi-version sections
        """
        query = {"is_multi_version": True}
        if code:
            query["code"] = code

        cursor = self.sections.find(query)
        sections = []
        for doc in cursor:
            doc.pop("_id", None)
            sections.append(Section(**doc))
        return sections

    def count_sections(self, code: str) -> int:
        """Count total sections for a code.

        Args:
            code: Code abbreviation

        Returns:
            Number of sections
        """
        return self.sections.count_documents({"code": code})

    def bulk_upsert_sections(self, sections: List[SectionCreate]) -> int:
        """Bulk insert or update sections.

        Args:
            sections: List of sections to upsert

        Returns:
            Number of sections upserted
        """
        if not sections:
            return 0

        operations = []
        for section in sections:
            section_dict = section.model_dump()
            section_dict["last_updated"] = datetime.utcnow()

            # Remove created_at from $set to avoid conflict with $setOnInsert
            section_dict.pop("created_at", None)

            operations.append(
                UpdateOne(
                    {"code": section.code, "section": section.section},
                    {
                        "$set": section_dict,
                        "$setOnInsert": {"created_at": datetime.utcnow()}
                    },
                    upsert=True
                )
            )

        result = self.sections.bulk_write(operations, ordered=False)
        logger.info(f"Bulk upserted {result.upserted_count + result.modified_count} sections")
        return result.upserted_count + result.modified_count

    # ==================== Code CRUD Operations ====================

    def create_code(self, code: CodeCreate) -> Code:
        """Create a new code entry.

        Args:
            code: Code data

        Returns:
            Created code
        """
        code_dict = code.model_dump()
        code_dict["created_at"] = datetime.utcnow()
        code_dict["last_updated"] = datetime.utcnow()
        code_dict["total_sections"] = 0
        code_dict["single_version_count"] = 0
        code_dict["multi_version_count"] = 0
        code_dict["processed_sections"] = 0
        code_dict["stage1_completed"] = False
        code_dict["stage2_completed"] = False
        code_dict["stage3_completed"] = False

        self.codes.insert_one(code_dict)
        logger.info(f"Created code: {code.code}")

        return Code(**code_dict)

    def get_code(self, code: str) -> Optional[Code]:
        """Get code metadata.

        Args:
            code: Code abbreviation

        Returns:
            Code if found, None otherwise
        """
        doc = self.codes.find_one({"code": code})
        if doc:
            doc.pop("_id", None)
            return Code(**doc)
        return None

    def update_code(self, code: str, update: CodeUpdate) -> Optional[Code]:
        """Update code metadata.

        Args:
            code: Code abbreviation
            update: Update data

        Returns:
            Updated code if found, None otherwise
        """
        update_dict = {k: v for k, v in update.model_dump().items() if v is not None}
        update_dict["last_updated"] = datetime.utcnow()

        result = self.codes.find_one_and_update(
            {"code": code},
            {"$set": update_dict},
            return_document=True
        )

        if result:
            result.pop("_id", None)
            logger.debug(f"Updated code: {code}")
            return Code(**result)
        return None

    def upsert_code(self, code: CodeCreate) -> Code:
        """Insert or update a code.

        Args:
            code: Code data

        Returns:
            Created or updated code
        """
        existing = self.get_code(code.code)

        if existing:
            update = CodeUpdate(**code.model_dump(exclude={"code"}))
            return self.update_code(code.code, update)
        else:
            return self.create_code(code)

    def get_all_codes(self) -> List[Code]:
        """Get all codes.

        Returns:
            List of all codes
        """
        cursor = self.codes.find({})
        codes = []
        for doc in cursor:
            doc.pop("_id", None)
            codes.append(Code(**doc))
        return codes

    # ==================== Job CRUD Operations ====================

    def create_job(self, job_create: JobCreate) -> Job:
        """Create a new job.

        Args:
            job_create: Job data

        Returns:
            Created job
        """
        # Generate job ID
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        job_id = f"{job_create.code.lower()}_{timestamp}"

        job_dict = {
            "job_id": job_id,
            "code": job_create.code,
            "status": JobStatus.PENDING,
            "stage": "not_started",
            "total_sections": 0,
            "processed_sections": 0,
            "failed_sections": 0,
            "progress_percentage": 0.0,
            "started_at": None,
            "finished_at": None,
            "estimated_completion": None,
            "error_message": None,
            "failed_section_urls": [],
            "metadata": job_create.metadata or {},
            "created_at": datetime.utcnow(),
            "last_updated": datetime.utcnow(),
        }

        self.jobs.insert_one(job_dict)
        logger.info(f"Created job: {job_id}")

        return Job(**job_dict)

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID.

        Args:
            job_id: Job identifier

        Returns:
            Job if found, None otherwise
        """
        doc = self.jobs.find_one({"job_id": job_id})
        if doc:
            doc.pop("_id", None)
            return Job(**doc)
        return None

    def update_job(self, job_id: str, update: JobUpdate) -> Optional[Job]:
        """Update a job.

        Args:
            job_id: Job identifier
            update: Update data

        Returns:
            Updated job if found, None otherwise
        """
        update_dict = {k: v for k, v in update.model_dump().items() if v is not None}
        update_dict["last_updated"] = datetime.utcnow()

        result = self.jobs.find_one_and_update(
            {"job_id": job_id},
            {"$set": update_dict},
            return_document=True
        )

        if result:
            result.pop("_id", None)
            logger.debug(f"Updated job: {job_id}")
            return Job(**result)
        return None

    def get_recent_jobs(self, limit: int = 10) -> List[Job]:
        """Get most recent jobs.

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of recent jobs
        """
        cursor = self.jobs.find({}).sort("created_at", -1).limit(limit)
        jobs = []
        for doc in cursor:
            doc.pop("_id", None)
            jobs.append(Job(**doc))
        return jobs

    def get_active_jobs(self) -> List[Job]:
        """Get all active (pending or running) jobs.

        Returns:
            List of active jobs
        """
        cursor = self.jobs.find({"status": {"$in": [JobStatus.PENDING, JobStatus.RUNNING]}})
        jobs = []
        for doc in cursor:
            doc.pop("_id", None)
            jobs.append(Job(**doc))
        return jobs


# Singleton instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get or create the database manager singleton.

    Returns:
        DatabaseManager instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        _db_manager.connect()
    return _db_manager


def close_db_manager() -> None:
    """Close the database manager connection."""
    global _db_manager
    if _db_manager:
        _db_manager.disconnect()
        _db_manager = None
