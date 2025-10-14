"""
Failure Logger
Helper functions to log section failures during processing
"""

import logging
import traceback
from typing import Optional
from datetime import datetime

from pipeline.core.database import DatabaseManager
from pipeline.models.failed_section import FailedSection, FailureType, RetryStatus

logger = logging.getLogger(__name__)


class FailureLogger:
    """
    Helper class for logging section failures to MongoDB
    """

    def __init__(self, db_manager: DatabaseManager):
        """Initialize failure logger"""
        self.db = db_manager

    def log_failure(
        self,
        code: str,
        section: str,
        url: str,
        failure_type: FailureType,
        error_message: str,
        stage: str,
        is_multi_version: bool = False,
        batch_number: Optional[int] = None,
        include_stack_trace: bool = False
    ) -> None:
        """
        Log a section failure to MongoDB

        Args:
            code: Code abbreviation
            section: Section number
            url: Section URL
            failure_type: Type of failure
            error_message: Error message
            stage: Processing stage (stage2_content, stage3_multi_version)
            is_multi_version: Whether section is multi-version
            batch_number: Batch number if applicable
            include_stack_trace: Whether to include stack trace
        """
        stack_trace = None
        if include_stack_trace:
            stack_trace = traceback.format_exc()

        failed_section = FailedSection(
            code=code,
            section=section,
            url=url,
            failure_type=failure_type,
            error_message=error_message[:500],  # Truncate long messages
            stack_trace=stack_trace,
            stage=stage,
            batch_number=batch_number,
            is_multi_version=is_multi_version,
            retry_status=RetryStatus.PENDING,
            failed_at=datetime.now()
        )

        # Check if already exists
        existing = self.db.db['failed_sections'].find_one({
            'code': code,
            'section': section
        })

        if existing:
            # Update existing record
            self.db.db['failed_sections'].update_one(
                {'code': code, 'section': section},
                {
                    '$set': {
                        'error_message': error_message[:500],
                        'failed_at': datetime.now(),
                        'retry_status': RetryStatus.PENDING
                    },
                    '$inc': {'attempt_number': 1}
                }
            )
            logger.debug(f"Updated existing failure record for {code} §{section}")
        else:
            # Insert new record
            self.db.db['failed_sections'].insert_one(failed_section.dict())
            logger.debug(f"Logged new failure for {code} §{section}")

    def log_api_error(
        self,
        code: str,
        section: str,
        url: str,
        error: Exception,
        stage: str,
        is_multi_version: bool = False,
        batch_number: Optional[int] = None
    ) -> None:
        """Log an API error failure"""
        self.log_failure(
            code=code,
            section=section,
            url=url,
            failure_type=FailureType.API_ERROR,
            error_message=f"Firecrawl API error: {str(error)}",
            stage=stage,
            is_multi_version=is_multi_version,
            batch_number=batch_number,
            include_stack_trace=True
        )

    def log_timeout(
        self,
        code: str,
        section: str,
        url: str,
        timeout_duration: float,
        stage: str,
        is_multi_version: bool = False,
        batch_number: Optional[int] = None
    ) -> None:
        """Log a timeout failure"""
        failure_type = (
            FailureType.MULTI_VERSION_TIMEOUT
            if is_multi_version
            else FailureType.TIMEOUT
        )

        self.log_failure(
            code=code,
            section=section,
            url=url,
            failure_type=failure_type,
            error_message=f"Request timed out after {timeout_duration}s",
            stage=stage,
            is_multi_version=is_multi_version,
            batch_number=batch_number
        )

    def log_parse_error(
        self,
        code: str,
        section: str,
        url: str,
        error: Exception,
        stage: str,
        is_multi_version: bool = False,
        batch_number: Optional[int] = None
    ) -> None:
        """Log a parsing error failure"""
        self.log_failure(
            code=code,
            section=section,
            url=url,
            failure_type=FailureType.PARSE_ERROR,
            error_message=f"Content parsing failed: {str(error)}",
            stage=stage,
            is_multi_version=is_multi_version,
            batch_number=batch_number,
            include_stack_trace=True
        )

    def log_empty_content(
        self,
        code: str,
        section: str,
        url: str,
        stage: str,
        is_multi_version: bool = False,
        batch_number: Optional[int] = None
    ) -> None:
        """Log an empty content failure"""
        self.log_failure(
            code=code,
            section=section,
            url=url,
            failure_type=FailureType.EMPTY_CONTENT,
            error_message="No content extracted from page (may be repealed)",
            stage=stage,
            is_multi_version=is_multi_version,
            batch_number=batch_number
        )

    def log_network_error(
        self,
        code: str,
        section: str,
        url: str,
        error: Exception,
        stage: str,
        is_multi_version: bool = False,
        batch_number: Optional[int] = None
    ) -> None:
        """Log a network error failure"""
        self.log_failure(
            code=code,
            section=section,
            url=url,
            failure_type=FailureType.NETWORK_ERROR,
            error_message=f"Network error: {str(error)}",
            stage=stage,
            is_multi_version=is_multi_version,
            batch_number=batch_number
        )

    def get_failure_count(self, code: str) -> int:
        """Get count of failed sections for a code"""
        return self.db.db['failed_sections'].count_documents({'code': code})

    def get_pending_retry_count(self, code: str) -> int:
        """Get count of sections pending retry"""
        return self.db.db['failed_sections'].count_documents({
            'code': code,
            'retry_status': RetryStatus.PENDING
        })


# Convenience function for quick logging
def log_section_failure(
    db: DatabaseManager,
    code: str,
    section: str,
    url: str,
    error: Exception,
    stage: str,
    is_multi_version: bool = False,
    batch_number: Optional[int] = None
) -> None:
    """
    Quick convenience function to log a section failure

    Args:
        db: Database manager
        code: Code abbreviation
        section: Section number
        url: Section URL
        error: Exception that occurred
        stage: Processing stage
        is_multi_version: Whether section is multi-version
        batch_number: Batch number if applicable
    """
    logger_instance = FailureLogger(db)

    error_str = str(error).lower()

    # Determine failure type based on error message
    if 'timeout' in error_str:
        logger_instance.log_timeout(
            code, section, url, 60.0, stage, is_multi_version, batch_number
        )
    elif 'network' in error_str or 'connection' in error_str:
        logger_instance.log_network_error(
            code, section, url, error, stage, is_multi_version, batch_number
        )
    elif 'parse' in error_str or 'extract' in error_str:
        logger_instance.log_parse_error(
            code, section, url, error, stage, is_multi_version, batch_number
        )
    elif 'empty' in error_str or 'no content' in error_str:
        logger_instance.log_empty_content(
            code, section, url, stage, is_multi_version, batch_number
        )
    else:
        logger_instance.log_api_error(
            code, section, url, error, stage, is_multi_version, batch_number
        )
